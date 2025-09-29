# 🚀 AI App Builder Demo (Lovable Lite Clone)

This project is a simplified **clone of Lovable**, an AI-powered app builder built with **LangGraph, FastAPI, and Next.js**.  
It demonstrates how users can create simple applications by just describing them in natural language.  

The system takes the user’s prompt, **plans the app**, **scaffolds the code**, **builds a live preview**, and finally allows exporting the app code.

---
## control Panel ui
<img width="1366" height="683" alt="lang" src="https://github.com/user-attachments/assets/952b4fd8-bae8-470a-9bf4-4ddfc4e10202" />


## 📌 Overview

- **Frontend:** Next.js (React + Tailwind + shadcn/ui + Heroicons)  
- **Backend:** FastAPI + LangGraph (Python)  
- **Flow:**  
  1. User enters a natural language **prompt** (e.g., *"Create a dashboard with a navbar, stats cards, and a dark theme"*).  
  2. System logs each step in a **Task Log** (Spec Synthesizer → Planner → Scaffolder → Builder → Preview → Export).  
  3. The app is automatically scaffolded with clean **React + Tailwind code**.  
  4. A **Preview** of the app is shown.  
  5. Users can **export** the generated code.  

---

## ⚙️ How It Works

1. **User Prompt**  
   - You describe the app you want in plain English.  
   - Example:  
     ```
     Create an e-commerce product page with a grid of items, search bar, and blue theme.
     ```

2. **LangGraph Workflow**  
   - **Spec Synthesizer:** Converts your prompt into structured requirements.  
   - **Planner:** Breaks down the app into components (Navbar, Sidebar, Cards, Buttons, etc.).  
   - **Scaffolder:** Generates base React + Tailwind code.  
   - **Builder:** Assembles all components into a working app.  
   - **Preview & Export:** Lets you test the app and export it as a Next.js project.  

3. **Task Logs**  
   - Every step is tracked so you can see how the app was generated.  

---

## ▶️ How to Run(locally)

### 1. Clone the Repo
- git clone https://github.com/yourusername/lovable-lite.git
### 2. Setup virtual environment (optional)
- python -m venv venv
- source venv/bin/activate   # Linux/Mac
- venv\Scripts\activate      # Windows
### 3. Install dependencies
- pip install -r requirements.txt
### 4. Run locally
- python run.py
- Visit: http://localhost:8081

## 🐳 Running with Docker

### 1. Clone the Repo
- git clone https://github.com/yourusername/lovable-lite.git
### 2. Build Docker image
- docker compose build
### 3. Run container
- docker compose up -d
### 4. Check logs(optional)
-docker compose logs -f


## 🌐 Access the App

- FastAPI backend → http://localhost:8081
- App preview (iframe / Next.js) → http://localhost:3000


## ⚙️ Environment Variables

- Copy .env.example to .env and set your own keys (e.g., OPENAI_API_KEY, langsmith key).
- ( - OPENAI_API_KEY="enter your key"
    - OPENAI_MODEL=gpt-4o-mini
    - LANGCHAIN_TRACING_V2=true
    - LANGCHAIN_API_KEY="enter your key"
    - LANGCHAIN_PROJECT=loveable_lite)
- The container automatically picks up .env via docker-compose.yml.

## 🎮 Usage

- Open the app in browser
- Enter a prompt (e.g., “Build me a chatbot UI with Tailwind and icons”)
- Watch Task Logs update step-by-step
- See Preview App load live
- Click Export App to download the Next.js project as a .zip


## 📌 Features

- ✅ AI-driven app generation workflow
- ✅ Task logs for debugging
- ✅ Live preview of app
- ✅ Export full Next.js project
- ✅ Works locally & in Docker








