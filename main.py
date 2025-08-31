from src.agents.avot_tyme import AVOTTyme

def main():
    tyme = AVOTTyme()
    print("Welcome to Node Tyme Open 🧙")
    while True:
        query = input("🌀 Ask AVOT-Tyme: ")
        response = tyme.respond(query)
        print(f"🔁 {response}")

if __name__ == "__main__":
    main()
