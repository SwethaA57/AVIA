from transformers import AutoTokenizer, AutoModelForQuestionAnswering
from openvino.tools import mo
import torch
import os

model_name = "distilbert-base-uncased-distilled-squad"
save_dir = "models"

os.makedirs(save_dir, exist_ok=True)

# Load model
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Export to ONNX
dummy_input = tokenizer("What is your name?", "My name is ChatGPT.", return_tensors="pt")
torch.onnx.export(
    model,
    (dummy_input["input_ids"], dummy_input["attention_mask"]),
    f"{save_dir}/model.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["start_logits", "end_logits"],
    opset_version=14,
    dynamic_axes={"input_ids": {0: "batch_size", 1: "seq_len"}, "attention_mask": {0: "batch_size", 1: "seq_len"}}
)

print("✅ ONNX model exported.")

# Convert ONNX to OpenVINO IR
mo.convert_model(
    input_model=f"{save_dir}/model.onnx",
    output_dir=save_dir,
    model_name="distilbert-base-uncased-distilled-squad"
)

print("✅ Model converted to OpenVINO format.")
