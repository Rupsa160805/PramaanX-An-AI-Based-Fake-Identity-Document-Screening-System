import os

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import resnet18


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "ml",
    "tampering_model.pth"
)


transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Tampering model not found: {MODEL_PATH}\n"
            "Train the model first using ml/train.py."
        )

    model = resnet18(weights=None)

    model.fc = nn.Linear(
        model.fc.in_features,
        2
    )

    model.load_state_dict(
        torch.load(
            MODEL_PATH,
            map_location=DEVICE
        )
    )

    model = model.to(DEVICE)
    model.eval()

    return model


def run_tampering(image_path):
    model = load_model()

    image = Image.open(
        image_path
    ).convert("RGB")

    image = transform(image)

    image = image.unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(image)

        probabilities = torch.softmax(
            outputs,
            dim=1
        )

        tampered_probability = (
            probabilities[0][1].item()
        )

    return float(tampered_probability)
