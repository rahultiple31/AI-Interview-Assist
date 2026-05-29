# AI Interview Assist

Windows 10/11 desktop app for interview preparation and answer drafting.

This version does five things:

- Provides a realtime assist screen for typed or pasted live transcripts.
- Saves priority question/answer pairs and uses them before any other reference.
- Imports resume and interview reference documents from TXT, MD, CSV, PDF, and DOCX.
- Drafts an answer from your saved materials, with optional GPT-style generation when `OPENAI_API_KEY` is set.
- Builds a Windows executable and installer through GitHub Actions.

The app does not capture audio from Teams, Meet, or other live calls. It is designed for consent-based preparation, drafting, and practice.

## Requirement Coverage

| Requirement | Current implementation |
| --- | --- |
| Windows 10/11 app | Enforced by runtime OS checks, PowerShell build script, and installer `MinVersion=10.0`. The packaged installer targets 64-bit compatible Windows. |
| Teams/Meet spoken questions | Realtime mode supports typed/pasted consent-based transcripts and auto-drafts from the latest detected question. Covert meeting audio capture is intentionally not implemented. |
| ChatGPT/Codex-style answers | Optional OpenAI-compatible answer generation through `OPENAI_API_KEY`; local reference mode without an API key. |
| Provided Q&A first priority | Saved Q&A is searched before document references. |
| Resume/document references | TXT, MD, CSV, PDF, and DOCX references are imported and searched for related context. |
| Windows install package | GitHub Actions builds a Windows EXE and Inno Setup installer artifact. |

## Requirements

- Windows 10 or Windows 11, 64-bit compatible
- Python 3.11 or newer

## Run Locally

```powershell
python -m pip install -r requirements.txt
.\run.ps1
```

Without an API key, the app works in local reference mode. It will return the best saved Q&A match or a document-based outline.

To enable AI drafting:

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:AI_INTERVIEW_MODEL="gpt-4o-mini"
.\run.ps1
```

Optional compatible endpoint:

```powershell
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
```

## Realtime Assist

Open the `Realtime` tab, paste or type a live transcript, and keep `Auto draft` enabled. The app detects the latest question after a short pause and drafts an answer from:

1. Saved priority Q&A
2. Imported resume/interview documents
3. Optional OpenAI-compatible model when `OPENAI_API_KEY` is set

Use `Draft Now` when you want to generate immediately.

## Build Windows EXE

```powershell
.\build_windows.ps1
```

The portable application is copied to:

```text
final-product\AI-Interview-Assist\AIInterviewAssist.exe
```

## Build Installer

After building the EXE, open `installer\AIInterviewAssist.iss` in Inno Setup and compile it. The installer has `MinVersion=10.0`, so it only installs on Windows 10 and Windows 11.

The final installer is saved to:

```text
final-product\AI-Interview-Assist-Setup.exe
```

## GitHub Actions Build

The workflow at `.github/workflows/windows-build.yml` runs only on a Windows runner. It performs a syntax check, builds the PyInstaller executable, compiles the Inno Setup installer, and uploads both as artifacts.

After the workflow finishes, download:

- `AI-Interview-Assist-final-product` for the complete final output folder
- `AI-Interview-Assist-final-product-installer` for only the setup EXE
- `AI-Interview-Assist-final-product-portable` for only the portable app folder

The complete final product artifact contains:

```text
final-product\AI-Interview-Assist\AIInterviewAssist.exe
final-product\AI-Interview-Assist-Setup.exe
```

The generated installer is still Windows-only because the installer script uses:

```text
MinVersion=10.0
ArchitecturesAllowed=x64compatible
```

The application also checks the OS at runtime and exits unless it is Windows 10 or Windows 11.

## Reference Priority

When you ask a question:

1. Saved Q&A is searched first.
2. If a close saved question is found, its answer is the primary source.
3. If no close Q&A exists, the app searches imported documents and pasted references.
4. If `OPENAI_API_KEY` is available, the AI drafts from those references and is instructed not to invent experience.
