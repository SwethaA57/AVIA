from transformers import AutoModelForQuestionAnswering, AutoTokenizer
import torch

# Load model and tokenizer
model_name = "distilbert-base-uncased-distilled-squad"
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Sample input for export (dummy text)
question = "What is the capital of France?"
context = "Paris is the capital of France and is known for the Eiffel Tower."
inputs = tokenizer(question, context, return_tensors="pt")

# Export to ONNX
torch.onnx.export(
    model,                                          # Model
    (inputs["input_ids"], inputs["attention_mask"]),# Inputs
    "distilbert-base-uncased-distilled-squad.onnx", # Output ONNX filename
    input_names=["input_ids", "attention_mask"],
    output_names=["start_logits", "end_logits"],
    dynamic_axes={
        "input_ids": {0: "batch_size", 1: "sequence_length"},
        "attention_mask": {0: "batch_size", 1: "sequence_length"},
        "start_logits": {0: "batch_size", 1: "sequence_length"},
        "end_logits": {0: "batch_size", 1: "sequence_length"},
    },
    opset_version=14
)

print("✅ Exported ONNX model successfully.")
