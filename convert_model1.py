import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Load pretrained model and tokenizer
model = T5ForConditionalGeneration.from_pretrained("t5-small")
tokenizer = T5Tokenizer.from_pretrained("t5-small")
model.eval()

# Dummy input
text = "generate quiz: what is gravity"
inputs = tokenizer(text, return_tensors="pt", padding=True)
decoder_input_ids = torch.tensor([[model.config.decoder_start_token_id]])

# Export
torch.onnx.export(
    model,
    (inputs["input_ids"], inputs["attention_mask"], decoder_input_ids),
    "model.onnx",
    input_names=["input_ids", "attention_mask", "decoder_input_ids"],
    output_names=["output"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "decoder_input_ids": {0: "batch", 1: "seq"}
    },
    opset_version=14
)

print("✅ Exported model.onnx successfully")
