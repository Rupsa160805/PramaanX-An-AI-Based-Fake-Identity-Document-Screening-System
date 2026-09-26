import os

import torch
import torch.nn as nn
import torch.optim as optim

from torchvision import datasets, transforms
from torchvision.models import resnet18, ResNet18_Weights
from torch.utils.data import DataLoader, random_split


# =========================
# SETTINGS
# =========================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DATASET_DIR = os.path.join(
    BASE_DIR,
    "dataset"
)

MODEL_PATH = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__)
    ),
    "tampering_model.pth"
)

BATCH_SIZE = 8
EPOCHS = 10
LEARNING_RATE = 0.0001


DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# =========================
# IMAGE TRANSFORMATION
# =========================

transform = transforms.Compose([
    transforms.Resize((224, 224)),

    transforms.RandomRotation(5),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# =========================
# LOAD DATASET
# =========================

dataset = datasets.ImageFolder(
    DATASET_DIR,
    transform=transform
)


print("Dataset location:", DATASET_DIR)
print("Classes:", dataset.classes)
print("Total images:", len(dataset))


if len(dataset) < 10:
    raise ValueError(
        "Dataset is too small. Add more images to "
        "dataset/genuine and dataset/tampered."
    )


# =========================
# TRAIN / VALIDATION SPLIT
# =========================

train_size = int(
    0.8 * len(dataset)
)

val_size = len(dataset) - train_size


train_dataset, val_dataset = random_split(
    dataset,
    [train_size, val_size]
)


train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False
)


# =========================
# LOAD RESNET18
# =========================

weights = ResNet18_Weights.DEFAULT

model = resnet18(
    weights=weights
)


# Replace final layer
model.fc = nn.Linear(
    model.fc.in_features,
    2
)


model = model.to(DEVICE)


# =========================
# LOSS + OPTIMIZER
# =========================

criterion = nn.CrossEntropyLoss()

optimizer = optim.Adam(
    model.parameters(),
    lr=LEARNING_RATE
)


# =========================
# TRAINING
# =========================

for epoch in range(EPOCHS):

    model.train()

    total_loss = 0
    correct = 0
    total = 0


    for images, labels in train_loader:

        images = images.to(DEVICE)
        labels = labels.to(DEVICE)


        optimizer.zero_grad()


        outputs = model(images)


        loss = criterion(
            outputs,
            labels
        )


        loss.backward()

        optimizer.step()


        total_loss += loss.item()


        _, predicted = torch.max(
            outputs,
            1
        )


        total += labels.size(0)

        correct += (
            predicted == labels
        ).sum().item()


    train_accuracy = (
        correct / total
        if total > 0
        else 0
    )


    # =========================
    # VALIDATION
    # =========================

    model.eval()

    val_correct = 0
    val_total = 0


    with torch.no_grad():

        for images, labels in val_loader:

            images = images.to(DEVICE)
            labels = labels.to(DEVICE)


            outputs = model(images)


            _, predicted = torch.max(
                outputs,
                1
            )


            val_total += labels.size(0)

            val_correct += (
                predicted == labels
            ).sum().item()


    val_accuracy = (
        val_correct / val_total
        if val_total > 0
        else 0
    )


    print(
        f"Epoch {epoch + 1}/{EPOCHS} | "
        f"Loss: {total_loss:.4f} | "
        f"Train Accuracy: {train_accuracy:.4f} | "
        f"Validation Accuracy: {val_accuracy:.4f}"
    )


# =========================
# SAVE MODEL
# =========================

torch.save(
    model.state_dict(),
    MODEL_PATH
)


print()
print("Training completed!")
print("Model saved to:")
print(MODEL_PATH)
