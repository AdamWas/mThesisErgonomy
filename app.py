from __future__ import annotations

import argparse
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS_FILE = APP_DIR / "models.txt"
DEFAULT_PROMPT_TEMPLATE = APP_DIR / "prompt.md"
DEFAULT_OUTPUT_DIR = APP_DIR / "results"
DEFAULT_TEMPERATURE = 0

TECHNOLOGIES = {
    "rest": {
        "solution_type": "REST",
        "paths": [
            "REST/Server/Program.cs",
            "REST/Server/RestTemperatureServer.csproj",
            "REST/Client/Program.cs",
            "REST/Client/RestTemperatureClient.csproj",
        ],
    },
    "grpc": {
        "solution_type": "gRPC",
        "paths": [
            "gRPC/Protos/temperature.proto",
            "gRPC/Server/Program.cs",
            "gRPC/Server/GrpcTemperatureServer.csproj",
            "gRPC/Client/Program.cs",
            "gRPC/Client/GrpcTemperatureClient.csproj",
        ],
    },
    "gc": {
        "solution_type": "Graftcode",
        "paths": [
            "Graftcode/GCTemperatureServer/TemperatureService.cs",
            "Graftcode/GCTemperatureServer/GCTemperatureServer.csproj",
            "Graftcode/GCTemperatureClient/Program.cs",
            "Graftcode/GCTemperatureClient/GCTemperatureClient.csproj",
        ],
    },
}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_models(models_file: Path, cli_models: list[str]) -> list[str]:
    models: list[str] = []

    for value in cli_models:
        models.extend(part.strip() for part in value.split(",") if part.strip())

    if models:
        return models

    if not models_file.exists():
        raise RuntimeError(
            f"No models provided. Add model IDs to {models_file} or pass --model."
        )

    with models_file.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                models.append(line)

    if not models:
        raise RuntimeError(f"No active model IDs found in {models_file}.")

    return models


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "model"


def read_input_code(paths: list[str]) -> str:
    sections: list[str] = []

    for relative_path in paths:
        path = APP_DIR / relative_path
        language = language_for_path(path)
        content = path.read_text(encoding="utf-8")
        sections.append(
            f"=== FILE: {relative_path} ===\n"
            f"{language}\n"
            f"{content.rstrip()}\n"
        )

    return "\n".join(sections)


def language_for_path(path: Path) -> str:
    match path.suffix.lower():
        case ".cs":
            return "csharp"
        case ".csproj":
            return "xml"
        case ".proto":
            return "protobuf"
        case _:
            return "text"


def build_prompt(template: str, technology_key: str) -> str:
    technology = TECHNOLOGIES[technology_key]
    return (
        template.replace("SOLUTION_TYPE", technology["solution_type"])
        .replace("INPUT_CODE", read_input_code(technology["paths"]))
    )


def completion_to_dict(completion: Any) -> dict[str, Any]:
    if hasattr(completion, "model_dump"):
        return completion.model_dump(mode="json")
    if hasattr(completion, "dict"):
        return completion.dict()
    return json.loads(json.dumps(completion, default=str))


def usage_to_dict(completion: Any) -> dict[str, Any]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump(mode="json")
    if hasattr(usage, "dict"):
        return usage.dict()
    if isinstance(usage, dict):
        return usage
    return json.loads(json.dumps(usage, default=str))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(APP_DIR))
    except ValueError:
        return str(path)


def append_usage_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp_utc",
        "technology",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "usage_json",
        "prompt_file",
        "response_file",
        "metadata_file",
    ]
    write_header = not path.exists()

    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def run_benchmark(args: argparse.Namespace) -> None:
    from openai import OpenAI

    load_env_file(APP_DIR / ".env.local")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment or .env.local.")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": args.referer,
            "X-Title": args.title,
        },
    )

    models = load_models(args.models_file, args.model)
    template = args.prompt_template.read_text(encoding="utf-8")
    technologies = args.technology or list(TECHNOLOGIES)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    for technology in technologies:
        prompt = build_prompt(template, technology)

        for model in models:
            model_dir = args.output_dir / technology / slugify(model)
            prompt_path = model_dir / f"{timestamp}_prompt.md"
            response_path = model_dir / f"{timestamp}_response.md"
            metadata_path = model_dir / f"{timestamp}_metadata.json"
            print(f"Running {technology} with {model}...")

            completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=args.temperature,
                extra_body={"usage": {"include": True}},
            )

            content = completion.choices[0].message.content or ""
            metadata = {
                "timestamp_utc": timestamp,
                "technology": technology,
                "solution_type": TECHNOLOGIES[technology]["solution_type"],
                "model": model,
                "temperature": args.temperature,
                "prompt_template": display_path(args.prompt_template),
                "prompt_file": display_path(prompt_path),
                "prompt_characters": len(prompt),
                "source_files": TECHNOLOGIES[technology]["paths"],
                "usage": usage_to_dict(completion),
                "completion": completion_to_dict(completion),
            }

            write_text(prompt_path, prompt)
            write_text(response_path, content)
            write_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))
            append_usage_row(
                args.output_dir / "usage.csv",
                {
                    "timestamp_utc": timestamp,
                    "technology": technology,
                    "model": model,
                    "prompt_tokens": metadata["usage"].get("prompt_tokens"),
                    "completion_tokens": metadata["usage"].get("completion_tokens"),
                    "total_tokens": metadata["usage"].get("total_tokens"),
                    "usage_json": json.dumps(metadata["usage"], ensure_ascii=False),
                    "prompt_file": display_path(prompt_path),
                    "response_file": display_path(response_path),
                    "metadata_file": display_path(metadata_path),
                },
            )

            print(f"Saved {display_path(response_path)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the same prompt through selected OpenRouter models."
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help="OpenRouter model ID. Can be repeated or comma-separated. Overrides models.txt.",
    )
    parser.add_argument(
        "--models-file",
        type=Path,
        default=DEFAULT_MODELS_FILE,
        help="File with one OpenRouter model ID per line.",
    )
    parser.add_argument(
        "--technology",
        choices=sorted(TECHNOLOGIES),
        action="append",
        help="Technology to run. Can be repeated. Defaults to all.",
    )
    parser.add_argument(
        "--prompt-template",
        type=Path,
        default=DEFAULT_PROMPT_TEMPLATE,
        help="Prompt template containing SOLUTION_TYPE and INPUT_CODE placeholders.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for responses and token usage logs.",
    )
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument("--referer", default="https://twoj-projekt.local")
    parser.add_argument("--title", default="Magisterka benchmark")
    return parser.parse_args()


if __name__ == "__main__":
    run_benchmark(parse_args())
