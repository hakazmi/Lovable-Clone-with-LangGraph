# 🚀 AI App Builder Demo (Lovable Lite Clone)

This project is a simplified **clone of Lovable**, an AI-powered app builder built with **LangGraph, FastAPI, and Next.js**.  
It demonstrates how users can create simple applications by just describing them in natural language.  

The system takes the user’s prompt, **plans the app**, **scaffolds the code**, **builds a live preview**, and finally allows exporting the app code.

---
## control panel 
<img width="1366" height="683" alt="lang" src="https://github.com/user-attachments/assets/ab3eab66-34f8-46fc-871c-1cd0e6052d54" />

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

## ▶️ How to Run

### 1. Clone the Repo

git clone https://github.com/yourusername/ai-app-builder-demo.git
cd ai-app-builder-demo

### 2. Setup Backend (FastAPI + LangGraph)
- cd backend
- python -m venv venv
- source venv/bin/activate   # On Windows: venv\Scripts\activate
- pip install -r requirements.txt
- uvicorn main:app --reload --port 8080
- Backend will run on: http://localhost:8080
### 3. Setup Frontend (Next.js)

- cd template\next-basic
- npm install
- npm run dev
- Frontend will run on: http://localhost:3000




