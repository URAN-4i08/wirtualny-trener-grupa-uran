# Uruchamianie aplikacji

Skrypty startowe podzielone według systemu operacyjnego. Uruchamiaj **backend** i **frontend** w dwóch osobnych terminalach.

## Windows (PowerShell)

**Jedna komenda (backend + frontend):**

```powershell
.\odpalanie\windows\start-app.ps1
```

**Dwa terminale (osobno):**

```powershell
# Terminal 1 — backend
.\odpalanie\windows\start-backend.ps1

# Terminal 2 — frontend
.\odpalanie\windows\start-frontend.ps1
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173  

## macOS (Terminal)

Przy pierwszym użyciu nadaj uprawnienia do wykonania:

```bash
chmod +x odpalanie/macos/*.sh
```

**Jedna komenda (backend + frontend):**

```bash
./odpalanie/macos/start-app.sh
```

**Dwa terminale (osobno):**

```bash
# Terminal 1 — backend
./odpalanie/macos/start-backend.sh

# Terminal 2 — frontend
./odpalanie/macos/start-frontend.sh
```

## Wymagania

| Składnik | Windows | macOS |
|----------|---------|-------|
| Python | 3.11 | 3.11 (`python3.11`) |
| Node.js | 20+ | 20+ |
| Plik `.env` | w katalogu głównym projektu | j.w. |

Szczegóły konfiguracji: [URUCHOMIENIE_I_SZKOLENIE.md](../URUCHOMIENIE_I_SZKOLENIE.md).
