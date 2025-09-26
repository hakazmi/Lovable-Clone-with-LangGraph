from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
from graph.engine import run_graph
from tools import repo_tool
from tools.zip_tool import zip_dir
import shutil, os, time, signal, subprocess
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI()

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
RUNS = {}

def kill_all_existing_servers(slug_to_keep=None):
    for slug, run in list(RUNS.items()):
        if slug == slug_to_keep:
            continue
        pid = run.get("pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Killed previous PID {pid} for {slug}")
                time.sleep(1)
            except Exception as e:
                print(f"Failed to kill PID {pid}: {e}")
        
        repo = run.get("repo_path")
        if repo and os.path.exists(repo):
            shutil.rmtree(repo, ignore_errors=True)
        if slug != slug_to_keep:
            del RUNS[slug]
    
    try:
        subprocess.run(
            "netstat -aon | findstr :3000 | findstr LISTENING | for /F \"tokens=5\" %a in ('more') do taskkill /F /PID %a",
            shell=True, capture_output=True
        )
        print("Cleared port 3000 of any lingering processes")
    except Exception as e:
        print(f"Failed to clear port 3000: {e}")

def detect_intent(prompt, slug=None):
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that analyzes user prompts for a Next.js app builder. Determine if the prompt is for a new app build or an edit to an existing app. If the prompt contains words like 'change', 'edit', 'modify', 'update', or refers to specific components like 'navbar', 'color', etc., classify it as an edit. Output a JSON object with 'action' (build/edit), 'slug' (if edit, use the provided slug or null), and 'details' (parsed intent or features)."},
                {"role": "user", "content": f"Prompt: {prompt}\nExisting slug (if any): {slug}"}
            ],
            max_tokens=150,
            temperature=0.1
        )
        intent = response.choices[0].message.content
        import json
        return json.loads(intent)
    except Exception as e:
        print(f"OpenAI intent detection failed: {e}")
        # Fallback: if slug exists and prompt has edit keywords, treat as edit
        edit_keywords = ['change', 'edit', 'modify', 'update', 'color', 'navbar', 'button', 'background']
        if slug and any(keyword in prompt.lower() for keyword in edit_keywords):
            return {"action": "edit", "slug": slug, "details": prompt}
        else:
            return {"action": "edit" if slug else "build", "slug": slug, "details": prompt}

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("control.html", {"request": request})

@app.post("/process", response_class=HTMLResponse)
def process(request: Request, prompt: str = Form(...), slug: str = Form(None)):
    # Clean the slug by removing any quotes or special characters
    if slug:
        slug = slug.strip('"\'')  # Remove quotes from slug
    
    intent = detect_intent(prompt, slug)
    action = intent["action"]
    provided_slug = intent.get("slug") or slug
    details = intent["details"]

    if action == "build":
        if provided_slug and provided_slug in RUNS:
            action = "edit"
        else:
            kill_all_existing_servers(provided_slug)
            # Clean the slug generation
            slug_base = "_".join(prompt.strip().lower().split()[:6])
            # Remove any special characters from slug
            slug_base = "".join(c for c in slug_base if c.isalnum() or c in ['_', '-'])
            provided_slug = f"{slug_base}-{int(time.time())}"
            init_state = {"user_prompt": str(details), "slug": provided_slug, "task_log": [], "file_diffs": [], "repo_path": None}
            RUNS[provided_slug] = init_state
            result = run_graph(init_state)
            RUNS[provided_slug] = result
            if not result.get("repo_path"):
                print(f"Warning: repo_path not set for slug {provided_slug}")
                result["repo_path"] = repo_tool.create_work_dir("work", provided_slug)
            if result.get("run_url"):
                print(f"New server started at {result['run_url']} with PID {result.get('pid')}")
            return templates.TemplateResponse(
                "_task_log.html",
                {"request": request, "task_log": result.get("task_log", []), "run_url": result.get("run_url"), "slug": provided_slug}
            )
    elif action == "edit":
        # Clean the provided_slug for matching
        if provided_slug:
            provided_slug = provided_slug.strip('"\'')
        
        # Try to find the run with exact match first
        run = RUNS.get(provided_slug)
        
        # If not found, try partial matching (in case of slug variations)
        if not run and provided_slug:
            matching_slugs = [k for k in RUNS.keys() if provided_slug in k]
            if matching_slugs:
                provided_slug = matching_slugs[0]  # Use the first match
                run = RUNS.get(provided_slug)
                print(f"Found matching slug: {provided_slug}")
        
        if not run:
            print(f"Run not found for slug: {provided_slug}")
            print(f"Available slugs: {list(RUNS.keys())}")
            raise HTTPException(404, f"Run not found for slug: {provided_slug}")
            
        pid = run.get("pid")
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Killed PID {pid} for {provided_slug}")
                time.sleep(1)
            except Exception as e:
                print(f"Failed to kill PID {pid}: {e}")
        
        # For edits, we need to run the graph with the edit instruction
        edit_prompt = f"Original app: {run.get('user_prompt', '')}. Edit requirement: {details}"
        
        # Update the state with edit prompt
        edit_state = {
            "user_prompt": edit_prompt,
            "slug": provided_slug,
            "repo_path": run.get("repo_path"),
            "task_log": run.get("task_log", []),
            "file_diffs": run.get("file_diffs", []),
            "edit_mode": True  # Add flag to indicate edit mode
        }
        
        result = run_graph(edit_state)
        RUNS[provided_slug] = result
        
        if not result.get("repo_path") and run.get("repo_path"):
            result["repo_path"] = run.get("repo_path")
            
        if result.get("run_url"):
            print(f"Edited server started at {result['run_url']} with PID {result.get('pid')}")
            
        return templates.TemplateResponse(
            "_task_log.html",
            {"request": request, "task_log": result.get("task_log", []), "run_url": result.get("run_url"), "slug": provided_slug}
        )
    else:
        raise HTTPException(400, "Invalid action detected")

@app.get("/export/{slug}")
def export(slug: str):
    run = RUNS.get(slug)
    if not run:
        raise HTTPException(404, "Run not found")
    repo = run.get("repo_path")
    if not repo:
        raise HTTPException(400, "No repo available")
    zip_path = zip_dir(repo, os.path.join("work", slug, "artifact"))
    return FileResponse(zip_path, media_type="application/zip", filename=os.path.basename(zip_path))

@app.post("/reset/{slug}")
def reset(slug: str):
    run = RUNS.get(slug)
    if not run:
        raise HTTPException(404, "Run not found")
    pid = run.get("pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    workdir = run.get("repo_path")
    if workdir and os.path.exists(workdir):
        shutil.rmtree(workdir, ignore_errors=True)
    del RUNS[slug]
    return {"ok": True}
