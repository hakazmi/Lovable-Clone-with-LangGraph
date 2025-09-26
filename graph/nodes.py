import os
import json
import shutil
from typing import Any, Dict
from datetime import datetime
from pathlib import Path
from tools import repo_tool, shell_tool, zip_tool
from tools.error_parser import parse_json_response  # Import the new parser tool
from openai import OpenAI
import time
import httpx
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    client = None

TEMPLATE_DIR = str(Path(__file__).resolve().parents[1] / "templates" / "next-basic")

def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def log_entry(name: str, status: str, note: str = "") -> Dict[str, Any]:
    return {"node": name, "when": now_ts(), "status": status, "note": note}

def call_openai(name: str, messages, max_tokens=4096, temperature=0.2):  # Increased default max_tokens
    if not client:
        raise RuntimeError("OPENAI_API_KEY not set in environment")
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature
    )
    print(f"Raw {name} response: {response.choices[0].message.content}")  # Debug
    return response.choices[0].message.content

@traceable
def agent_node(name: str, system_prompt: str, user_prompt: str, tools: dict, state: dict) -> dict:
    try:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        
        # Adjust max_tokens for Scaffolder to allow larger responses
        max_tokens = 4096 if name == "Scaffolder" else 1200
        
        reasoning = call_openai(name, messages, max_tokens=max_tokens, temperature=0.2)
        
        # Use the LLM parser to clean and extract the action dict
        action = parse_json_response(reasoning)
        print(f"Parsed action: {action}")  # Enhanced debugging
        if not isinstance(action, dict):
            action = {"output": {}}

        tool_results = {}
        tools_to_call = action.get("tools", {})
        for tool_name, args in tools_to_call.items():
            if tool_name in tools:
                try:
                    tool_func = tools[tool_name]
                    result = tool_func(**args) if args else tool_func()
                    tool_results[tool_name] = result
                except Exception as e:
                    tool_results[tool_name] = f"Error: {e}"

        updates = {}
        task_log = state.get("task_log", []) + [log_entry(name, "ok", reasoning[:200])]

        if name == "SpecSynthesizer":
            spec = action.get("output", {})
            if isinstance(spec, str):
                try:
                    spec = json.loads(spec)
                except json.JSONDecodeError:
                    spec = {"entities": [], "pages": ["/"], "features": [], "components": []}
            updates = {"spec": spec, "task_log": task_log}

        elif name == "Planner":
            plan = action.get("output", [])
            if isinstance(plan, str):
                try:
                    plan = json.loads(plan)
                except json.JSONDecodeError:
                    plan = [{"id": "default_task", "description": "Default task", "files": ["pages/index.js"]}]
            updates = {"plan": plan, "task_log": task_log}

        elif name == "Scaffolder":
            file_map = action.get("output", {})
            
            # Enhanced debugging
            print(f"Scaffolder: Initial action: {action}")
            print(f"Scaffolder: Initial file_map before extraction: {file_map}")
            
            # Ensure file_map is extracted from nested structure if present
            if "output" in action and isinstance(action["output"], dict):
                file_map = action["output"]
            elif not file_map:  # Handle flattened structure as fallback
                file_map = {k: v for k, v in action.items() if k in ['pages/index.js', 'pages/api/data.js', 'tailwind.config.js', 'postcss.config.js', 'package.json', 'styles/globals.css']}
            
            # Debug after extraction
            print(f"Scaffolder: Initial file_map after extraction: {file_map}")
            
            # Ensure file_map is a dictionary and has expected keys
            if not isinstance(file_map, dict) or len(file_map) == 0:
                print(f"Scaffolder: Invalid or empty file_map, using fallback")
                # Use correct fallback with proper package.json and tailwind setup
                file_map = {
                    "pages/index.js": "import Head from 'next/head';\n\nexport default function Home() {\n  return (\n    <div className=\"min-h-screen bg-gray-100 p-6\">\n      <Head>\n        <title>Default Dashboard</title>\n      </Head>\n      <main>\n        <h1 className=\"text-2xl font-bold\">Default Content</h1>\n      </main>\n    </div>\n  );\n}",
                    "package.json": '{\n  "name": "crm-dashboard",\n  "version": "0.1.0",\n  "private": true,\n  "scripts": {\n    "dev": "next dev -p 3000",\n    "build": "next build",\n    "start": "next start -p 3000"\n  },\n  "dependencies": {\n    "next": "^15.5.3",\n    "react": "^19.1.1",\n    "react-dom": "^19.1.1"\n  },\n  "devDependencies": {\n    "tailwindcss": "^3.4.10",\n    "autoprefixer": "^10.4.20",\n    "postcss": "^8.4.41"\n  }\n}',
                    "tailwind.config.js": 'module.exports = {\n  content: [\n    "./pages/**/*.{js,ts,jsx,tsx}",\n    "./components/**/*.{js,ts,jsx,tsx}",\n    "./app/**/*.{js,ts,jsx,tsx}"\n  ],\n  theme: { \n    extend: {} \n  },\n  plugins: [],\n};',
                    "styles/globals.css": "@tailwind base;\n@tailwind components;\n@tailwind utilities;"
                }
            
            print(f"Scaffolder: Processed file_map with {len(file_map)} files: {list(file_map.keys())}")
            
            slug = state.get("slug") or f"app-{int(time.time())}"
            repo_path = state.get("repo_path") or repo_tool.create_work_dir("work", slug)
            os.makedirs(repo_path, exist_ok=True)

            try:
                # More aggressive cleanup before template copy
                if os.path.exists(repo_path):
                    print(f"Scaffolder: Repo path exists, cleaning up: {repo_path}")
                    try:
                        import subprocess
                        subprocess.run(['taskkill', '/f', '/t', '/im', 'node.exe'], 
                                     capture_output=True, shell=True)
                        time.sleep(2)  # Wait for processes to die
                        shutil.rmtree(repo_path, ignore_errors=True)
                        time.sleep(1)  # Wait for cleanup
                    except Exception as cleanup_error:
                        print(f"Scaffolder: Cleanup error (continuing): {cleanup_error}")
                
                # Copy template first, but only if repo doesn't exist yet
                if not os.path.exists(os.path.join(repo_path, "package.json")):
                    print(f"Scaffolder: Copying template from {TEMPLATE_DIR} to {repo_path}")
                    repo_tool.copy_template(TEMPLATE_DIR, repo_path)
                else:
                    print(f"Scaffolder: Template already exists, skipping copy")
                
                diffs = state.get("file_diffs", [])
                applied = 0
                
                # Write custom files AFTER template copy
                for rel_path, content in file_map.items():
                    target_full = os.path.join(repo_path, rel_path)
                    print(f"Scaffolder: Writing {len(content)} chars to {target_full}")
                    os.makedirs(os.path.dirname(target_full), exist_ok=True)
                    repo_tool.write_file(target_full, content)
                    diffs.append(f"Updated {rel_path}")
                    applied += 1
                    print(f"Scaffolder: Successfully wrote {rel_path}")
                
                print(f"Scaffolder: Applied {applied} file changes")
                updates = {
                    "repo_path": repo_path,
                    "slug": slug,
                    "file_diffs": diffs,
                    "task_log": task_log,
                    "intent_details": state.get("user_prompt", "Minimal Next.js dashboard")
                }
            except Exception as e:
                print(f"Scaffolder error: {e}")
                task_log.append(log_entry(name, "err", f"Failed to scaffold: {str(e)}"))
                updates = {"repo_path": repo_path, "slug": slug, "task_log": task_log}

        elif name == "Builder":
            repo_path = state.get("repo_path")
            if not repo_path or not os.path.exists(repo_path):
                return {**state, "last_error": "Invalid repo_path", "task_log": task_log + [log_entry(name, "err", "repo_path not set or invalid")]}

            build_logs = ""
            next_cache = os.path.join(repo_path, ".next")
            if os.path.exists(next_cache):
                shutil.rmtree(next_cache)
                print(f"Cleared Next.js cache at {next_cache}")

            code, out, err = shell_tool.run_command(["npm", "install"], cwd=repo_path)
            build_logs += "\n=== npm install ===\n" + out + "\n" + err
            print(f"Builder: npm install - code={code}, out={out}, err={err}")
            if code != 0:
                return {**state, "last_error": err, "build_logs": build_logs, "task_log": task_log + [log_entry(name, "err", f"npm install failed: {err}")]}

            code2, out2, err2 = shell_tool.run_command(["npm", "run", "build"], cwd=repo_path)
            build_logs += "\n=== npm run build ===\n" + out2 + "\n" + err2
            print(f"Builder: npm run build - code={code2}, out={out2}, err={err2}")
            if code2 != 0:
                return {**state, "last_error": err2, "build_logs": build_logs, "task_log": task_log + [log_entry(name, "err", f"build failed: {err2}")]}

            logfile_path = os.path.join(repo_path, "dev_server.log")
            pid = shell_tool.start_dev_server(repo_path, logfile_path)

            def check():
                try:
                    r = httpx.get("http://localhost:3000/api/health", timeout=1.0)
                    print(f"Health check response: status={r.status_code}, text={r.text}")
                    return r.status_code == 200
                except Exception as e:
                    print(f"Health check failed: {e}")
                    return False

            healthy = shell_tool.wait_for_url_check(check, timeout=30)
            status = "ok" if healthy else "err"
            note = f"pid={pid} healthy={healthy}"
            last_error = None if healthy else "Dev server not responding within timeout."
            
            # Track retry count
            retry_count = state.get("build_retry_count", 0)
            if last_error:
                retry_count += 1
                
            updates = {
                "repo_path": repo_path,
                "run_url": "http://localhost:3000" if healthy else None,
                "pid": pid,
                "build_logs": build_logs,
                "last_error": last_error,
                "build_retry_count": retry_count,
                "task_log": task_log + [log_entry(name, status, note)]
            }

        elif name == "Fixer":
            last_error = state.get('last_error', '')
            if not last_error:
                # No errors to fix
                updates = {
                    "task_log": task_log + [log_entry("Fixer", "noop", "no errors to fix")],
                    "fixer_applied_fixes": False
                }
                return {**state, **updates}
            
            file_map = action.get("output", {})
            
            # Use the LLM parser for Fixer as well if needed
            if isinstance(file_map, str):
                file_map = parse_json_response(file_map)
            
            # Extract nested output if needed
            if "output" in file_map and isinstance(file_map["output"], dict):
                file_map = file_map["output"]
            
            repo_path = state.get("repo_path", "")
            applied = 0
            diffs = state.get("file_diffs", [])
            
            # Handle the case where content might not be a string (like dict objects from bad LLM responses)
            for rel_path, content in file_map.items():
                if isinstance(content, str):
                    target_full = os.path.join(repo_path, rel_path)
                    os.makedirs(os.path.dirname(target_full), exist_ok=True)
                    repo_tool.write_file(target_full, content)
                    diffs.append(f"Fixed {rel_path}")
                    applied += 1
                elif isinstance(content, dict):
                    # Convert dict to JSON string for package.json files
                    target_full = os.path.join(repo_path, rel_path)
                    os.makedirs(os.path.dirname(target_full), exist_ok=True)
                    json_content = json.dumps(content, indent=2)
                    repo_tool.write_file(target_full, json_content)
                    diffs.append(f"Fixed {rel_path}")
                    applied += 1
            
            # Track if we actually fixed something
            fixer_made_changes = applied > 0
            previous_error = state.get("last_error") if fixer_made_changes else None
            last_error = None if fixer_made_changes else state.get("last_error")
            build_retry_count = state.get("build_retry_count", 0)
            
            updates = {
                "file_diffs": diffs, 
                "last_error": last_error,
                "previous_error": previous_error,
                "fixer_applied_fixes": fixer_made_changes,
                "build_retry_count": build_retry_count,
                "task_log": task_log + [log_entry(name, "ok" if applied > 0 else "noop", f"fixed_files={applied}")]
            }

        elif name == "PreviewDeploy":
            repo_path = state.get("repo_path")
            run_url = state.get("run_url")
            zip_path = tool_results.get("zip_dir", "")
            if repo_path and run_url:
                updates = {
                    "task_log": task_log + [log_entry(name, "ok", f"preview ready at {run_url}")],
                    "last_error": None,
                    "zip_path": zip_path
                }
            else:
                updates = {
                    "task_log": task_log + [log_entry(name, "err", "missing repo_path or run_url")],
                    "last_error": "missing repo_path or run_url"
                }

        return {**state, **updates}

    except Exception as e:
        task_log = state.get("task_log", []) + [log_entry(name, "err", str(e))]
        return {**state, "last_error": str(e), "task_log": task_log}


# === Node functions ===
@traceable
def spec_synthesizer(state: dict) -> dict:
    system_prompt = (
        "You are a software architect agent. "
        "Convert the user prompt into a structured JSON spec with entities, pages, features, and components. "
        "Output ONLY valid JSON in this format: "
        "{'output': {\"entities\": {...}, \"pages\": {...}, \"features\": {...}, \"components\": {...}}}. "
        "Make the spec detailed and specific to the user's request."
    )
    user_prompt = state.get("user_prompt", "Make a minimal Next.js app")
    return agent_node("SpecSynthesizer", system_prompt, user_prompt, {}, state)

@traceable
def planner(state: dict) -> dict:
    system_prompt = (
        "You are a planning agent. Break the app spec into 5–10 clear tasks with file paths. "
        "CRITICAL: The plan MUST include ALL specific features mentioned in the user prompt. "
        "If the user mentions specific colors, layouts, or components, ensure they are included in the plan. "
        "Output ONLY valid JSON in this format: "
        "{'output': [{\"task\": \"task_name\", \"description\": \"detailed_description\", \"files\": [\"path1\", \"path2\"]}]}. "
        "Focus on implementing the EXACT features mentioned in the spec."
    )
    user_prompt = f"Create a detailed plan for implementing this spec. Include ALL specific features mentioned by the user:\n{json.dumps(state.get('spec', {}), indent=2)}"
    return agent_node("Planner", system_prompt, user_prompt, {}, state)

@traceable
def scaffolder(state: dict) -> dict:
    tools = {"write_file": repo_tool.write_file}
    system_prompt = (
        "You are a Next.js developer. Create a MINIMAL but functional Next.js app that EXACTLY matches the user's request. "
        "CRITICAL: You MUST follow these user requirements PRECISELY:\n"
        "1. COLOR SCHEME: If user specifies colors (like 'purple and pink gradient'), use EXACTLY those colors\n"
        "2. LAYOUT: If user specifies layout (like 'fixed navbar'), implement EXACTLY that layout\n" 
        "3. COMPONENTS: If user specifies components (like 'calories card, steps card, workout summary'), create EXACTLY those components\n"
        "4. CONTENT: Include all specific elements mentioned (charts, cards, navigation items, etc.)\n\n"
        "Technical requirements:\n"
        "- Always set up Tailwind CSS with modern 'content' field in tailwind.config.js\n"
        "- Create pages/index.js with UI that MATCHES THE USER'S EXACT DESCRIPTION\n"
        "- Create pages/api/data.js with mock data relevant to the app type\n"
        "- Include proper package.json with tailwindcss, postcss, autoprefixer in devDependencies\n"
        "- Use Tailwind utility classes for styling, especially for specified color schemes\n\n"
        "Examples of EXACT matching:\n"
        "- User says 'purple and pink gradient' → Use bg-gradient-to-r from-purple-500 to-pink-500\n"
        "- User says 'fixed navbar' → Use fixed top-0 w-full z-50\n" 
        "- User says 'fitness dashboard with calories card' → Create actual calorie card with mock data\n"
        "- User says 'chart showing progress' → Include a chart placeholder or mock chart\n\n"
        "Output VALID JSON with double quotes only: "
        "{\"output\": {\"pages/index.js\": \"content\", \"tailwind.config.js\": \"content\", ...}}"
    )
    
    spec = state.get("spec", {})
    plan = state.get("plan", [])
    user_prompt_original = state.get("user_prompt", "")
    
    user_prompt = f"""
Create a Next.js app that EXACTLY matches this description:
"{user_prompt_original}"

SPECIFIC REQUIREMENTS TO FOLLOW PRECISELY:
- Implement the EXACT color scheme mentioned
- Create the EXACT layout described  
- Include ALL specified components and features
- Use Tailwind CSS for styling
- Make it look like a real, professional application

Generate the necessary files with proper Tailwind setup.
"""
    
    return agent_node("Scaffolder", system_prompt, user_prompt, tools, state)

@traceable
def builder(state: dict) -> dict:
    tools = {"run_command": shell_tool.run_command, "start_dev_server": shell_tool.start_dev_server}
    system_prompt = (
        "You are a build agent. Use `run_command` for ['npm', 'install'] and ['npm', 'run', 'build'] using Next.js commands, "
        "then use `start_dev_server` to start the Next.js development server with 'next dev'."
    )
    user_prompt = f"Repo path: {state.get('repo_path')}"
    return agent_node("Builder", system_prompt, user_prompt, tools, state)

@traceable
def fixer(state: dict) -> dict:
    tools = {"write_file": repo_tool.write_file}
    system_prompt = (
        "You are a fixer agent. Given build/run errors, suggest code fixes as JSON. "
        "For 'Missing script: \"build\"' errors, update package.json with Next.js-compatible scripts: 'build': 'next build', 'dev': 'next dev'. "
        "For 'Cannot find module tailwindcss' errors, update package.json to include tailwindcss, postcss, and autoprefixer in devDependencies with proper versions. "
        "IMPORTANT: Always provide the file path as the key and the complete file content as the value. "
        "Output VALID JSON with double quotes only in this exact format: "
        "{\"output\": {\"package.json\": \"complete file content here\"}} "
        "DO NOT use keys like 'relative_file_path' or 'complete_fixed_content_as_string'."
    )
    # ... rest of the function remains the same
    last_error = state.get('last_error', '')
    if not last_error:
        return {**state, "task_log": state.get("task_log", []) + [log_entry("Fixer", "noop", "no errors to fix")]}
    
    user_prompt = f"Fix this error: {last_error}\n\nRepo path: {state.get('repo_path')}\n\nProvide complete file content as strings. For package.json, include all required dependencies."
    return agent_node("Fixer", system_prompt, user_prompt, tools, state)

@traceable
def preview_deploy(state: dict) -> dict:
    tools = {"zip_dir": zip_tool.zip_dir}
    system_prompt = (
        "You are a deploy agent. Zip the repo into 'work/preview.zip'. "
        "Output: {'tools': {'zip_dir': {'repo': <repo_path>, 'out': 'work/preview.zip'}}}."
    )
    repo = state.get("repo_path")
    run_url = state.get("run_url")
    user_prompt = f"Repo: {repo}\nRunURL: {run_url}"
    return agent_node("PreviewDeploy", system_prompt, user_prompt, tools, state)