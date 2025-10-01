#!/usr/bin/env python3
import requests
import sys

def health_check():
    try:
        response = requests.get("http://localhost:8081/health", timeout=10)
        if response.status_code == 200:
            print("✅ Bot API Server est en bonne santé")
            return True
        else:
            print(f"❌ Statut HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

if __name__ == "__main__":
    if health_check():
        sys.exit(0)
    else:
        sys.exit(1)
