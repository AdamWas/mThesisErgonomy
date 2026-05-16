from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS_FILE = APP_DIR / "models.txt"
DEFAULT_OUTPUT_DIR = APP_DIR / "results"
DEFAULT_TEMPERATURE = 0
DEFAULT_MAX_TOKENS = 12000
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

CASES = {
    "temperature_extension": {
        "name": "Temperature extension",
        "prompt_template": APP_DIR / "prompt.md",
    },
    "amount_service": {
        "name": "Amount service",
        "prompt_template": APP_DIR / "prompt_amount_service.md",
    },
}

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


def replace_section_value(template: str, section_name: str, value: str) -> str:
    pattern = rf"(?ms)^{re.escape(section_name)}:\n.*?(?=\n[A-Z][A-Z ]*:\n|\Z)"
    replacement = f"{section_name}:\n{value}"
    updated, count = re.subn(pattern, replacement, template, count=1)
    if count:
        return updated
    return template.replace(section_name, value)


def build_prompt(template: str, technology_key: str) -> str:
    technology = TECHNOLOGIES[technology_key]
    prompt = replace_section_value(template, "SOLUTION_TYPE", technology["solution_type"])
    return prompt.replace("INPUT_CODE", read_input_code(technology["paths"]))


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


def fetch_supported_parameters(
    api_key: str, timeout_seconds: float
) -> dict[str, set[str]] | None:
    context = None
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass

    request = urllib.request.Request(
        OPENROUTER_MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout_seconds, context=context
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as error:
        print(f"Warning: could not fetch OpenRouter model metadata: {error}")
        return None

    supported_parameters: dict[str, set[str]] = {}
    for model in payload.get("data", []):
        model_id = model.get("id")
        if not isinstance(model_id, str):
            continue
        parameters = model.get("supported_parameters")
        if isinstance(parameters, list):
            supported_parameters[model_id] = {
                parameter for parameter in parameters if isinstance(parameter, str)
            }

    return supported_parameters


def supports_parameter(
    supported_parameters: dict[str, set[str]] | None, model: str, parameter: str
) -> bool:
    if supported_parameters is None:
        return False
    parameters = supported_parameters.get(model)
    if parameters is None:
        return True
    return parameter in parameters


def build_completion_kwargs(
    model: str,
    prompt: str,
    args: argparse.Namespace,
    supported_parameters: dict[str, set[str]] | None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "extra_body": {"usage": {"include": True}},
    }

    if args.temperature is not None and supports_parameter(
        supported_parameters, model, "temperature"
    ):
        kwargs["temperature"] = args.temperature

    if args.max_tokens is not None:
        if supports_parameter(supported_parameters, model, "max_tokens"):
            kwargs["max_tokens"] = args.max_tokens
        elif supports_parameter(supported_parameters, model, "max_completion_tokens"):
            kwargs["max_completion_tokens"] = args.max_tokens

    return kwargs


def request_metadata(kwargs: dict[str, Any], prompt_path: Path, prompt: str) -> dict[str, Any]:
    metadata = {
        key: value
        for key, value in kwargs.items()
        if key not in {"messages"}
    }
    metadata["messages"] = [
        {
            "role": "user",
            "content_file": display_path(prompt_path),
            "content_characters": len(prompt),
        }
    ]
    return metadata


def validate_usage(usage: dict[str, Any]) -> dict[str, Any]:
    required_fields = ["prompt_tokens", "completion_tokens", "total_tokens"]
    missing_fields = [
        field
        for field in required_fields
        if usage.get(field) is None
    ]
    return {
        "valid": not missing_fields,
        "missing_fields": missing_fields,
    }


def validate_response_format(content: str) -> dict[str, Any]:
    header_pattern = re.compile(
        r"(?m)^=== FILE: (?P<path>.+?) ===\n(?P<language>[^\n]+)\n"
    )
    headers = list(header_pattern.finditer(content))
    loose_header_count = len(re.findall(r"(?m)^=== FILE:", content))
    notes: list[str] = []

    if not content.strip():
        notes.append("empty_response")
    if not headers:
        notes.append("missing_file_headers")
    if loose_header_count != len(headers):
        notes.append("malformed_file_header")
    if headers:
        leading_text = content[: headers[0].start()].strip()
        if leading_text:
            notes.append("text_before_first_file")
    if "```" in content:
        notes.append("contains_markdown_fences")

    return {
        "valid": not notes,
        "file_count": len(headers),
        "notes": notes,
        "files": [
            {
                "path": match.group("path").strip(),
                "language": match.group("language").strip(),
            }
            for match in headers
        ],
    }


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
        "run_id",
        "request_id",
        "status",
        "case",
        "case_name",
        "technology",
        "solution_type",
        "model",
        "usage_valid",
        "missing_usage_fields",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "response_format_valid",
        "response_file_count",
        "response_format_notes",
        "error_type",
        "error_message",
        "duration_seconds",
        "prompt_characters",
        "request_parameters_json",
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
    technologies = args.technology or list(TECHNOLOGIES)
    selected_cases = build_selected_cases(args)
    supported_parameters = fetch_supported_parameters(
        api_key, args.model_metadata_timeout
    )
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = args.output_dir / run_id
    request_index = 0

    for case_key, case in selected_cases.items():
        template_path = case["prompt_template"]
        template = template_path.read_text(encoding="utf-8")

        for technology in technologies:
            prompt = build_prompt(template, technology)

            for model in models:
                request_index += 1
                request_id = f"{request_index:04d}"
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                model_dir = run_dir / case_key / technology / f"{request_id}_{slugify(model)}"
                prompt_path = model_dir / "prompt.md"
                response_path = model_dir / "response.md"
                metadata_path = model_dir / "metadata.json"
                print(f"Running {case_key} / {technology} with {model}...")

                write_text(prompt_path, prompt)
                completion = None
                content = ""
                error: dict[str, str] | None = None
                completion_kwargs = build_completion_kwargs(
                    model, prompt, args, supported_parameters
                )
                started_at = time.perf_counter()

                try:
                    completion = client.chat.completions.create(**completion_kwargs)
                    content = completion.choices[0].message.content or ""
                except Exception as exception:
                    error = {
                        "type": type(exception).__name__,
                        "message": str(exception),
                    }

                duration_seconds = round(time.perf_counter() - started_at, 3)
                usage = usage_to_dict(completion) if completion is not None else {}
                usage_validation = validate_usage(usage)
                response_validation = validate_response_format(content)
                status = "success"
                if error is not None:
                    status = "failed"
                elif not usage_validation["valid"]:
                    status = "invalid_usage"

                metadata = {
                    "timestamp_utc": timestamp,
                    "run_id": run_id,
                    "request_id": request_id,
                    "status": status,
                    "case": case_key,
                    "case_name": case["name"],
                    "technology": technology,
                    "solution_type": TECHNOLOGIES[technology]["solution_type"],
                    "model": model,
                    "model_metadata_available": (
                        supported_parameters is not None
                        and model in supported_parameters
                    ),
                    "model_supported_parameters": sorted(
                        supported_parameters.get(model, [])
                        if supported_parameters is not None
                        else []
                    ),
                    "temperature": args.temperature,
                    "max_tokens": args.max_tokens,
                    "duration_seconds": duration_seconds,
                    "prompt_template": display_path(template_path),
                    "prompt_file": display_path(prompt_path),
                    "response_file": display_path(response_path),
                    "metadata_file": display_path(metadata_path),
                    "prompt_characters": len(prompt),
                    "source_files": TECHNOLOGIES[technology]["paths"],
                    "request": request_metadata(completion_kwargs, prompt_path, prompt),
                    "usage": usage,
                    "usage_validation": usage_validation,
                    "response_validation": response_validation,
                    "error": error,
                    "completion": (
                        completion_to_dict(completion)
                        if completion is not None
                        else None
                    ),
                }

                write_text(response_path, content)
                write_text(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2))
                usage_row = {
                    "timestamp_utc": timestamp,
                    "run_id": run_id,
                    "request_id": request_id,
                    "status": status,
                    "case": case_key,
                    "case_name": case["name"],
                    "technology": technology,
                    "solution_type": TECHNOLOGIES[technology]["solution_type"],
                    "model": model,
                    "usage_valid": usage_validation["valid"],
                    "missing_usage_fields": ",".join(
                        usage_validation["missing_fields"]
                    ),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                    "response_format_valid": response_validation["valid"],
                    "response_file_count": response_validation["file_count"],
                    "response_format_notes": ",".join(response_validation["notes"]),
                    "error_type": error["type"] if error else "",
                    "error_message": error["message"] if error else "",
                    "duration_seconds": duration_seconds,
                    "prompt_characters": len(prompt),
                    "request_parameters_json": json.dumps(
                        metadata["request"], ensure_ascii=False
                    ),
                    "usage_json": json.dumps(usage, ensure_ascii=False),
                    "prompt_file": display_path(prompt_path),
                    "response_file": display_path(response_path),
                    "metadata_file": display_path(metadata_path),
                }
                append_usage_row(run_dir / "usage.csv", usage_row)
                append_usage_row(run_dir / case_key / "usage.csv", usage_row)
                append_usage_row(args.output_dir / "usage_all.csv", usage_row)

                print(f"Saved {display_path(response_path)} [{status}]")


def build_selected_cases(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    if args.prompt_template is not None:
        return {
            "custom": {
                "name": "Custom prompt",
                "prompt_template": args.prompt_template,
            }
        }

    case_keys = args.case or list(CASES)
    return {case_key: CASES[case_key] for case_key in case_keys}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run benchmark prompts through selected OpenRouter models."
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
        "--case",
        choices=sorted(CASES),
        action="append",
        help="Case to run. Can be repeated. Defaults to all cases.",
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
        help="Custom prompt template containing SOLUTION_TYPE and INPUT_CODE placeholders. Runs as a single custom case.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for responses and token usage logs.",
    )
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Maximum response tokens to request when supported by the model.",
    )
    parser.add_argument(
        "--model-metadata-timeout",
        type=float,
        default=10,
        help="Timeout in seconds for fetching OpenRouter model parameter metadata.",
    )
    parser.add_argument("--referer", default="https://twoj-projekt.local")
    parser.add_argument("--title", default="Magisterka benchmark")
    return parser.parse_args()


if __name__ == "__main__":
    run_benchmark(parse_args())
