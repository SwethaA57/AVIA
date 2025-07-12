from openvino.runtime import Core
from transformers import AutoTokenizer
import numpy as np

# Load OpenVINO model
core = Core()
model_path = "models/distilbert-base-uncased-distilled-squad.xml"
model = core.read_model(model_path)
compiled_model = core.compile_model(model, "CPU")

# Inputs and outputs
input_ids = compiled_model.input(0)
attention_mask = compiled_model.input(1)
output_start = compiled_model.output(0)
output_end = compiled_model.output(1)

# Tokenizer
tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased-distilled-squad")

def answer_doubt(context, question):
    inputs = tokenizer(
        question,
        context,
        return_tensors="np",
        padding="max_length",
        truncation=True,
        max_length=384
    )

    input_ids_np = inputs["input_ids"]
    attention_mask_np = inputs["attention_mask"]

    result = compiled_model({
        input_ids: input_ids_np,
        attention_mask: attention_mask_np
    })

    start_logits = result[output_start][0]
    end_logits = result[output_end][0]

    start = int(np.argmax(start_logits))
    end = int(np.argmax(end_logits))

    #  Debug print 
    print(f"Start: {start}, End: {end}, Score: {start_logits[start]:.2f} to {end_logits[end]:.2f}")

    # Safety check
    if end < start or end - start > 30:
        return "I'm sorry, I could not extract a confident answer. Please try rephrasing the question."

    answer_tokens = input_ids_np[0][start:end + 1]
    answer = tokenizer.decode(answer_tokens, skip_special_tokens=True).strip()

    return answer if answer else "I'm sorry, I could not find a confident answer in the content."

