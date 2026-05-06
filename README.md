# MigNar Application
Streamlit application to explore migration‑related narrative frames and meso narratives in UK news.

## Live App
**https://mignar.streamlit.app/**

If the live app is unstable, run it locally. Choose your operating system below:

---

## 🪟 Windows Instructions

### 1. Initial Setup (Do this once)
Open **Command Prompt** as Administrator and run:
```cmd
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.11 -e --source winget
winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```
*Close the Administrator window when finished.*

Open a normal **Command Prompt** and run:
```cmd
git clone https://github.com/oii-seeing-migration/MigNar_FrontEnd_Streamlit
cd MigNar_FrontEnd_Streamlit
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run navigation_page.py
```

### 2. Update and Run (Do this next time)
Open **Command Prompt** and run to update and start the app:
```cmd
cd MigNar_FrontEnd_Streamlit
git pull
venv\Scripts\activate
pip install -r requirements.txt
streamlit run navigation_page.py
```

---

## 🍎 Mac Instructions

### 1. Initial Setup (Do this once)
Open **Terminal** and run:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install git python
git clone https://github.com/oii-seeing-migration/MigNar_FrontEnd_Streamlit
cd MigNar_FrontEnd_Streamlit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run navigation_page.py
```

### 2. Update and Run (Do this next time)
Open **Terminal** and run to update and start the app:
```bash
cd MigNar_FrontEnd_Streamlit
git pull
source venv/bin/activate
pip install -r requirements.txt
streamlit run navigation_page.py
```

---

## 🐧 Linux Instructions

### 1. Initial Setup (Do this once)
Open **Terminal** and run:
```bash
sudo apt update && sudo apt install git python3 python3-venv python3-pip build-essential -y
git clone https://github.com/oii-seeing-migration/MigNar_FrontEnd_Streamlit
cd MigNar_FrontEnd_Streamlit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run navigation_page.py
```

### 2. Update and Run (Do this next time)
Open **Terminal** and run to update and start the app:
```bash
cd MigNar_FrontEnd_Streamlit
git pull
source venv/bin/activate
pip install -r requirements.txt
streamlit run navigation_page.py
```
