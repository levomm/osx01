#!/usr/bin/env python3
"""
osx01 - Lokaalne autonoomne AI agent (Claude Code'i avatud alternatiiv)
Kasutab Ollama't kohalike open source mudelitega.

Seadistus:
  1. Paigalda Ollama: https://ollama.com
  2. Tõmba mudel: ollama pull qwen2.5-coder:7b
  3. pip install openai rich
  4. Käivita: python osx01.py "sinu ülesanne"
     või UI-ga: python osx01_ui.py "sinu ülesanne"
"""

import os
import json
import subprocess
import fnmatch
import re

try:
    from openai import OpenAI
except ImportError:
    raise SystemExit("[viga] Puudub 'openai' pakett. Paigalda: pip install openai")

# ---------------------------------------------------------
# KLIENT - Ollama (OpenAI-ühilduv liides)
# ---------------------------------------------------------
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

client = OpenAI(
    base_url=f"{OLLAMA_HOST}/v1",
    api_key="ollama",
)

# Vaikimisi mudel - toetab tööriistakutseid
# Alternatiivid: "llama3.1:8b", "mistral:7b", "qwen2.5-coder:14b"
DEFAULT_MODEL = os.environ.get("OSX01_MODEL", "qwen2.5-coder:7b")

# ---------------------------------------------------------
# TÖÖRIISTAD (Claude Code'i tööriistakomplekt)
# ---------------------------------------------------------

def bash(command: str, timeout: int = 30) -> str:
    """Käivitab shell-käsu ja tagastab tulemuse."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
        )
        output = result.stdout
        if result.returncode != 0 and result.stderr:
            output += "\n[stderr]:\n" + result.stderr
        return output[:4000] if output.strip() else "(käsk lõpetati, väljundit polnud)"
    except subprocess.TimeoutExpired:
        return f"[viga] Käsk aegus ({timeout}s)"
    except Exception as e:
        return f"[viga] {str(e)}"


def read_file(file_path: str) -> str:
    """Loeb faili sisu."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines()
        numbered = "\n".join(f"{i+1}\t{line}" for i, line in enumerate(lines))
        return numbered[:6000]
    except Exception as e:
        return f"[viga] {str(e)}"


def write_file(file_path: str, content: str) -> str:
    """Loob uue faili või kirjutab olemasoleva täielikult üle."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Fail '{file_path}' salvestatud ({len(content)} tähemärki)."
    except Exception as e:
        return f"[viga] {str(e)}"


def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Asendab failis täpselt ühe tekstilõigu teisega."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        count = content.count(old_string)
        if count == 0:
            return "[viga] old_string ei leitud failist. Kontrolli, et tekst on täpselt õige."
        if count > 1:
            return f"[viga] old_string esineb {count} korda - tee see unikaalseks lisades rohkem konteksti."
        new_content = content.replace(old_string, new_string, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Muudatus tehtud failis '{file_path}'."
    except Exception as e:
        return f"[viga] {str(e)}"


def ls(path: str = ".") -> str:
    """Loetleb kausta sisu."""
    try:
        entries = sorted(os.listdir(path))
        lines = []
        for entry in entries:
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                lines.append(f"  {entry}/")
            else:
                size = os.path.getsize(full)
                lines.append(f"  {entry}  ({size} B)")
        return "\n".join(lines) if lines else "(tühi kaust)"
    except Exception as e:
        return f"[viga] {str(e)}"


def glob(pattern: str, path: str = ".") -> str:
    """Leiab failid glob-mustri järgi (nt '**/*.py')."""
    try:
        matches = []
        base = os.path.abspath(path)
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".next"}]
            for fname in files:
                rel = os.path.relpath(os.path.join(root, fname), base).replace("\\", "/")
                if fnmatch.fnmatch(rel, pattern):
                    matches.append(rel)
        matches.sort()
        return "\n".join(matches[:100]) if matches else "Ühtegi faili ei leitud."
    except Exception as e:
        return f"[viga] {str(e)}"


def grep(pattern: str, path: str = ".", include: str = "*") -> str:
    """Otsib tekstimustrit failidest (regex toetatud)."""
    try:
        results = []
        regex = re.compile(pattern)
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".next"}]
            for fname in files:
                if not fnmatch.fnmatch(fname, include):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for lineno, line in enumerate(f, 1):
                            if regex.search(line):
                                rel = os.path.relpath(fpath, path)
                                results.append(f"{rel}:{lineno}: {line.rstrip()}")
                                if len(results) >= 50:
                                    break
                except Exception:
                    continue
                if len(results) >= 50:
                    break
        return "\n".join(results) if results else "Vasteid ei leitud."
    except Exception as e:
        return f"[viga] {str(e)}"


# ---------------------------------------------------------
# TÖÖRIISTADE SKEEM LLM-I JAOKS
# ---------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Käivitab shell-käsu (ls, git, python, npm, jne). Kasuta keskkonnaga suhtlemiseks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell-käsk"},
                    "timeout": {"type": "integer", "description": "Maksimaalne aeg sekundites (vaikimisi 30)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Loeb faili sisu koos reanumbritega.",
            "parameters": {
                "type": "object",
                "properties": {"file_path": {"type": "string", "description": "Faili tee"}},
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Kirjutab faili täieliku sisu. Loob faili kui seda pole.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Faili tee"},
                    "content": {"type": "string", "description": "Faili täielik sisu"}
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Asendab failis täpselt ühe tekstilõigu. old_string peab olema unikaalne.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Faili tee"},
                    "old_string": {"type": "string", "description": "Asendatav tekst (peab esinema täpselt üks kord)"},
                    "new_string": {"type": "string", "description": "Uus tekst"}
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ls",
            "description": "Loetleb kausta sisu.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Kausta tee (vaikimisi '.')"}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Otsib faile nime mustri järgi, nt '**/*.py' või '*.json'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob-muster"},
                    "path": {"type": "string", "description": "Otsingukaust (vaikimisi '.')"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Otsib tekstimustrit failidest. Toetab regex-i.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Otsingumuster (regex)"},
                    "path": {"type": "string", "description": "Otsingukaust (vaikimisi '.')"},
                    "include": {"type": "string", "description": "Failimuster, nt '*.py' (vaikimisi kõik)"}
                },
                "required": ["pattern"]
            }
        }
    }
]

TOOL_MAP = {
    "bash": bash,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "ls": ls,
    "glob": glob,
    "grep": grep,
}

# ---------------------------------------------------------
# AGENDI TSÜKKEL
# ---------------------------------------------------------

SYSTEM_PROMPT = """Sa oled osx01 - võimekas, autonoomne AI agent, mis töötab lokaalselt.
Oled loodud Claude Code'i eeskujul - sinu eesmärk on lahendada koodiga seotud ülesandeid.

Sul on järgmised tööriistad:
- bash: käivita terminalis käske
- read_file: loe faili (koos reanumbritega)
- write_file: kirjuta faili täielik sisu
- edit_file: muuda faili osa (asenda täpne tekstilõik)
- ls: vaata kausta sisu
- glob: otsi faile nime mustri järgi
- grep: otsi tekstimustrit failidest

Töötamise põhimõtted:
1. Uuri enne koodi muutmist - loe failid, uuri struktuur
2. Kasuta edit_file olemasolevate failide muutmiseks, write_file uute loomiseks
3. Käivita käske, et kontrollida tulemust (nt python fail.py, git status)
4. Kui oled ülesande lõpetanud, selgita lühidalt mida tegid - ära kasuta tööriistu
"""


def run_agent(
    goal: str,
    model: str = DEFAULT_MODEL,
    max_steps: int = 20,
    on_step=None,   # callback(step: int)
    on_tool=None,   # callback(name: str, args: dict, result: str)
    on_done=None,   # callback(result: str)
):
    """
    Käivitab agendi.
    on_step(step)               - kutsutakse iga sammu alguses
    on_tool(name, args, result) - kutsutakse pärast iga tööriistakutset
    on_done(result)             - kutsutakse kui agent lõpetab
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": goal},
    ]

    for step in range(1, max_steps + 1):
        if on_step:
            on_step(step)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            result_text = msg.content or ""
            if on_done:
                on_done(result_text)
            return result_text

        for call in msg.tool_calls:
            fn_name = call.function.name

            # Vigase JSON korral saadetakse viga tagasi mudelile - ei krahhi agenti
            try:
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError as e:
                result = f"[viga] Vigane JSON tööriistakutses '{fn_name}': {e}"
                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": fn_name,
                    "content": result,
                })
                if on_tool:
                    on_tool(fn_name, {}, result)
                continue

            fn = TOOL_MAP.get(fn_name)
            result = fn(**args) if fn else f"[viga] Tundmatu tööriist: {fn_name}"

            if on_tool:
                on_tool(fn_name, args, result)

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": fn_name,
                "content": result,
            })

    msg = "Agent saavutas maksimaalse sammude piiri."
    if on_done:
        on_done(msg)
    return msg


# ---------------------------------------------------------
# KÄIVITAMINE (ilma UI-ta)
# ---------------------------------------------------------
if __name__ == "__main__":
    import sys

    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Uuri selle projekti struktuuri ja kirjuta lühike kokkuvõte mis see projekt on."

    print(f"\n{'='*60}\n  osx01 | mudel: {DEFAULT_MODEL}\n{'='*60}")
    print(f"Ülesanne: {goal}\n")

    def _on_step(s): print(f"\n[samm {s}] {'-'*40}")
    def _on_tool(n, a, r):
        first = str(next(iter(a.values()), "")) if a else ""
        print(f"  [{n}] {first[:60]}")
        print(f"   -> {r[:100].replace(chr(10), ' ')}{'...' if len(r) > 100 else ''}")
    def _on_done(r): print(f"\n✅ VALMIS:\n{r}")

    run_agent(goal, on_step=_on_step, on_tool=_on_tool, on_done=_on_done)
