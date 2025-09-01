from src.agents.avot_tyme import AVOTTyme

def main():
    tyme = AVOTTyme()
    print("🌐 Welcome to Node Tyme Open")
    while True:
        try:
            query = input("🌀 Ask AVOT-Tyme: ")
            if query.lower() in ["exit", "quit"]:
                print("👋 Exiting Node Tyme Open.")
                break
            response = tyme.respond(query)
            print(f"🧭 {response}")
        except Exception as e:
            print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    main()
