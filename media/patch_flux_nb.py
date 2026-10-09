#!/usr/bin/env python3
"""
image_flux2_klein.ipynb 의 생성 함수 셀(7번 섹션)을 실제 CLI 인자에 맞게 교체한다.

  python3 patch_flux_nb.py                       # 기본 파일명
  python3 patch_flux_nb.py 다른이름.ipynb

원본은 <파일명>.bak 으로 백업된다.

[근거] black-forest-labs/flux2 scripts/cli.py 는 Fire(main) 이고,
       def main(model_name=None, single_eval=False, prompt=None,
                debug_mode=False, cpu_offloading=False, **overwrite)
  - 모델 지정은 --name 이 아니라 --model_name
  - --single_eval 없이는 대화형 루프로 들어가 EOF 에서 'bye!' 로 종료
  - --output_dir 은 존재하지 않는다. 출력은 CWD/output/sample_N.png
"""
import json
import pathlib
import shutil
import sys

NEW_SOURCE = '''import subprocess, sys, shutil, tempfile, pathlib, os

MODEL_NAME = "flux.2-klein-4b"     # 4B = Apache-2.0. 9B는 비상업이라 서비스에 못 쓴다
NUM_STEPS  = 4                     # klein은 4-step distilled
GUIDANCE   = 1.0                   # klein은 distilled라 guidance=1.0 고정, 다른 값 주면 ValueError
SIZE       = 1024

if "9b" in MODEL_NAME:
    print("경고: klein 9B는 비상업 라이선스다. 상용 서비스에는 4B만 쓸 수 있다.")


def build_args(prompt, refs=None, seed=0, size=SIZE):
    """scripts/cli.py 는 Fire(main) 이라 main() 의 파라미터명이 곧 플래그다.

        main(model_name, single_eval, prompt, debug_mode, cpu_offloading, **overwrite)

    width/height/num_steps/guidance/seed/input_images 는 **overwrite 로 들어가
    Config 필드를 덮어쓴다.
    """
    args = [
        sys.executable, str(FLUX_DIR / "scripts" / "cli.py"),
        f"--model_name={MODEL_NAME}",
        "--single_eval=True",          # 없으면 대화형 루프로 빠져 아무것도 안 나온다
        "--prompt", prompt,
        f"--width={size}",
        f"--height={size}",
        f"--num_steps={NUM_STEPS}",
        f"--guidance={GUIDANCE}",
        f"--seed={seed}",
        # 48GB 카드에서 텍스트 인코더 + 트랜스포머를 동시에 올리면 스모크 테스트
        # 첫 호출에서부터 OOM 난다 (47.4GB 사용 중에 320MiB 못 늘림).
        # cpu_offloading 을 켜면 CLI 가 둘을 번갈아 CPU<->GPU 로 옮긴다.
        "--cpu_offloading=True",
    ]
    if refs:
        args.append("--input_images=" + ",".join(str(pathlib.Path(r).resolve()) for r in refs))
    return args


def gen(prompt, out_file, refs=None, seed=0, size=SIZE):
    """CLI 는 --output_dir 이 없고 '현재 작업 디렉토리/output/sample_N.png' 에 저장한다.
    그래서 cwd 를 임시 디렉토리로 두고 거기서 결과를 회수한다."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    args = build_args(prompt, refs=refs, seed=seed, size=size)
    env = dict(os.environ, PYTHONPATH=str(FLUX_DIR / "src"))

    r = subprocess.run(args, cwd=tmp, env=env, capture_output=True, text=True)
    made = sorted((tmp / "output").glob("*.png")) or sorted(tmp.glob("**/*.png"))

    if r.returncode != 0 or not made:
        print("--- CLI stdout ---"); print(r.stdout[-2000:])
        print("--- CLI stderr ---"); print(r.stderr[-2000:])
        print("--- tmp 내용 ---")
        for q in sorted(tmp.rglob("*")):
            print("   ", q.relative_to(tmp))
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(
            f"생성 실패 (returncode={r.returncode}, png {len(made)}개). "
            "위 stdout 의 인자 오류를 확인할 것."
        )

    out_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(made[-1]), out_file)
    shutil.rmtree(tmp, ignore_errors=True)
    return out_file


print("준비됨. 8번 셀(연결 확인)에서 한 장만 먼저 뽑아볼 것.")
'''


def main() -> int:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "image_flux2_klein.ipynb")
    if not path.exists():
        print(f"파일을 찾을 수 없다: {path.resolve()}")
        return 1

    nb = json.loads(path.read_text(encoding="utf-8"))
    hits = []
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "def build_args" in src and "def gen" in src:
            hits.append((i, cell))

    if not hits:
        print("교체 대상 셀을 못 찾았다 ('def build_args' 와 'def gen' 이 같이 있는 코드 셀).")
        print("노트북 구조가 바뀌었을 수 있다. 수동으로 교체할 것.")
        return 1
    if len(hits) > 1:
        print(f"대상 셀이 {len(hits)}개다. 첫 번째만 교체한다: 셀 #{hits[0][0]}")

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    idx, cell = hits[0]
    cell["source"] = NEW_SOURCE.splitlines(keepends=True)
    cell["outputs"] = []
    cell["execution_count"] = None

    path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"셀 #{idx} 교체 완료")
    print(f"백업      : {backup}")
    print()
    print("바뀐 내용:")
    print("  --name         -> --model_name")
    print("  --single_eval  추가 (없으면 대화형 루프로 빠진다)")
    print("  --output_dir   제거 (CLI 에 없는 인자)")
    print("  결과 회수      cwd/output/*.png 에서 가져오도록 수정")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())