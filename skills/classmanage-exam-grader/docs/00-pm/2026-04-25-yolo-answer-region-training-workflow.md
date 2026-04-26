# YOLO Answer-Region Training Workflow

This project's YOLO answer-region detector should be trained on question-crop images, not full exam pages.

## Why Question Crops

- The runtime detector in `packages/student_extraction/answer_region_detector.py` crops each question block first.
- Training on the same input shape keeps the data distribution closer to inference time.
- Korean school tests often use two-column layouts, shared passages, score tags, and wrapped options, so full-page labels are noisier than question-local labels.

## Recommended Classes

- `choice_answer_region`
- `short_answer_line`
- `descriptive_answer_area`

These classes are broad enough for the current hybrid pipeline and map cleanly onto Korean test formats such as `①~⑤`, blank lines, and larger descriptive writing zones.

## Local Dataset Layout

```text
data/yolo_answer_regions/
  images/
    train/
    val/
  labels/
    train/
    val/
  data.yaml
  README.md
```

Initialize it with:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.init_answer_region_yolo_dataset
```

## Training Command

```powershell
.\.venv\Scripts\python.exe -m apps.cli.train_answer_region_yolo --device cpu --model yolov8n.pt
```

If a CUDA-capable GPU is available, replace `--device cpu` with the appropriate device string supported by Ultralytics.

## Labeling Guidance

- Label the answer-writing target, not the full prompt text.
- For multiple choice, box the final answer blank or checkbox region that the student writes into.
- For short answer, box the answer line itself.
- For descriptive questions, box the student writing area rather than the entire question block.
- Keep train and validation splits at the question-crop level.

## Validation Criteria

Do not rely on mAP alone. Compare:

- answer-region box hit rate
- `review_only` fallback rate
- downstream OCR success rate
- teacher correction burden in review

## Runtime Handoff

After training, point `config.json` at the best checkpoint and switch the detector mode:

```json
"answer_region_detector": {
  "mode": "hybrid",
  "weights_path": "runs/detect/answer-region-yolo/weights/best.pt",
  "confidence": 0.25
}
```

OpenCV remains the fallback path when YOLO returns no usable region.
