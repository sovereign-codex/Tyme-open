import os
import subprocess

def menu():
    print("""
🔮 NODE TYME OPEN: MODE SELECTOR
Choose an operation mode:

1. 🧙 AVOT Agent Mode (main.py)
2. 🌐 Static Web Preview (serve index.html)
3. 🧪 Digital Lab Notebook (open Jupyter)
4. 🧭 Web Scraper Console (demo run)
5. 📜 Scroll Compiler (md to HTML/pdf)
6. ❌ Exit
""")
    return input("Enter number (1–6): ")

while True:
    mode = menu()

    if mode == "1":
        print("\nLaunching AVOT Agent Interface...\n")
        subprocess.run(["python3", "main.py"])

    elif mode == "2":
        print("\nStarting Static Web Server on port 8080...\n")
        subprocess.run(["python3", "-m", "http.server", "8080"])

    elif mode == "3":
        print("\nLaunching Jupyter (simulate)...\n")
        subprocess.run(["echo", "Simulated Jupyter Launch (to be integrated externally)"])

    elif mode == "4":
        print("\n[Web Scraper] Searching Arxiv for 'plasma desalinization'...\n")
        subprocess.run(["echo", "Simulated scrape: https://arxiv.org/search?q=plasma+desalinization"])

    elif mode == "5":
        print("\n[Scroll Compiler] Converting example.md to HTML...\n")
        if os.path.exists("docs/example.md"):
            os.system("pandoc docs/example.md -s -o docs/example.html")
            print("✅ Scroll compiled to HTML: docs/example.html")
        else:
            print("❌ 'docs/example.md' not found.")

    elif mode == "6":
        print("Exiting... 🌀")
        break
    else:
        print("Invalid choice. Please select 1–6.")
