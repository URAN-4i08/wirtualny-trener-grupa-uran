import requests
from supabase import Client, create_client

from backend.config import SUPABASE_KEY, SUPABASE_URL

supabase_client: Client | None = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Pomyślnie zainicjalizowano Supabase w backendzie.")
    except Exception as e:
        print(f"Błąd inicjalizacji Supabase: {e}")


def save_training_session(user_id, source, start_time, end_time, stats, access_token=None):
    if not SUPABASE_URL or not SUPABASE_KEY or not user_id:
        print("[supabase] Brak konfiguracji lub user_id, pomijam zapis treningu.")
        return

    if not access_token:
        print("[supabase] Brak tokenu sesji użytkownika, pomijam zapis treningu.")
        return

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

        training_payload = {
            "user_id": user_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "source": source,
            "overall_score": stats.get("overall_score", 0),
            "status": "completed",
        }

        training_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/trainings",
            headers=headers,
            json=training_payload,
            timeout=15,
        )
        if not training_response.ok:
            print(f"[supabase] Błąd zapisu treningu: {training_response.status_code} {training_response.text}")
            return

        training_data = training_response.json()
        if not training_data:
            print("[supabase] Baza nie zwróciła id treningu po zapisie.")
            return

        training_id = training_data[0]["id"]

        stats_payload = {
            "training_id": training_id,
            "total_contacts": stats.get("total_contacts", 0),
            "avg_knee_angle": stats.get("avg_knee_angle", 0),
            "posture_warnings_count": stats.get("posture_warnings_count", 0),
            "avg_contact_score": stats.get("avg_contact_score", 0),
        }
        stats_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/training_stats",
            headers=headers,
            json=stats_payload,
            timeout=15,
        )
        if not stats_response.ok:
            print(f"[supabase] Błąd zapisu statystyk: {stats_response.status_code} {stats_response.text}")
            return

        print(f"Zapisano trening dla użytkownika {user_id}")
    except Exception as e:
        print(f"Błąd zapisu do Supabase: {e}")
