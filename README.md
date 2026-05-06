# MigNar Application
Streamlit application to explore migration‑related narrative frames and meso narratives in UK news.

## Live App
Access the deployed version on Streamlit Cloud here:  
**https://mignar.streamlit.app/**

If the live app is unstable or you want to use it on your own computer, follow this step-by-step guide. You do not need any coding experience! Just open your computer's "Terminal" (Mac/Linux) or "Command Prompt" (Windows) and copy-paste the commands below.

---

## Part 1: One-Time System Setup (Prerequisites)

Choose the instructions for your Operating System to install the necessary tools (Git, Python, and required libraries).

### 🪟 Windows Users
1. Click the Windows Start menu, type `cmd`, right-click **Command Prompt**, and select **Run as administrator** (if prompted, click Yes).
2. Install **Git** (to download the app) by copy-pasting this text and hitting Enter:
   ```cmd
   winget install --id Git.Git -e --source winget
   ```
3. Install **Python** (to run the app) by copy-pasting:
   ```cmd
   winget install --id Python.Python.3.11 -e --source winget
   ```
4. Install **C++ Build Tools** (needed for some background tasks). This is a large download and might take 10-15 minutes. Copy-paste:
   ```cmd
   winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
   ```
5. **IMPORTANT:** Close your Command Prompt completely, and open a normal (non-administrator) Command Prompt to continue.

### 🍎 Mac Users
1. Open the **Terminal** app (Press `Cmd + Space`, type "Terminal" and press Enter).
2. Install **Homebrew** (a tool to easily download software) by copy-pasting this command (it may ask for your computer password):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install **Git** and **Python**:
   ```bash
   brew install git python
   ```

### 🐧 Linux Users (Ubuntu/Debian)
1. Open your Terminal.
2. Install the necessary tools by copy-pasting:
   ```bash
   sudo apt update && sudo apt install git python3 python3-venv python3-pip build-essential -y
   ```

---

## Part 2: Downloading & Setting Up the App

Now that your computer has the right tools, let's download the MigNar app. Copy-paste these commands into your terminal one by one, pressing Enter after each:

1. **Download the app folder to your computer:**
   ```bash
   git clone https://github.com/oii-seeing-migration/MigNar_FrontEnd_Streamlit
   ```

2. **Go inside the folder you just downloaded:**
   ```bash
   cd MigNar_FrontEnd_Streamlit
   ```

3. **Create a safe "virtual" space for the app so you don't mess up your computer:**
   *(Windows Users)*
   ```cmd
   python -m venv venv
   ```
   *(Mac/Linux Users)*
   ```bash
   python3 -m venv venv
   ```

4. **Activate the safe space:**
   *(Windows Users)*
   ```cmd
   venv\Scripts\activate
   ```
   *(Mac/Linux Users)*
   ```bash
   source venv/bin/activate
   ```
   *(You should now see `(venv)` at the start of your typing line).*

5. **Install the app's specific parts:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Part 3: Running the App

Whenever you want to use the app, make sure you are inside the `MigNar_FrontEnd_Streamlit` folder and your `venv` is active (Part 2, steps 2 and 4). Then, run this command:

```bash
streamlit run navigation_page.py
```

A window should automatically pop up in your internet browser showing the app! 
Leave the black terminal window open while you use the app. When you are totally finished, you can just close the terminal.

---

## Part 4: Updating the App

If the developers have made changes or improvements, you don't need to do Part 1 and Part 2 all over again. Just open your terminal, go to the folder, and download the new updates. Copy-paste these one by one:

1. **Go to the app folder:**
   ```bash
   cd MigNar_FrontEnd_Streamlit
   ```
2. **Download the latest changes:**
   ```bash
   git pull
   ```
3. **Activate your environment:**
   *(Windows)*
   ```cmd
   venv\Scripts\activate
   ```
   *(Mac/Linux)*
   ```bash
   source venv/bin/activate
   ```
4. **Install any new requirements:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the app again:**
   ```bash
   streamlit run navigation_page.py
   ```
