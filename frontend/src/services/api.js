export const verifyDocument = async (file) => {
    const formData = new FormData();
    formData.append("document", file);

    const response = await fetch("/api/v1/verify", {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to verify document");
    }

    return response.json();
};

export const checkHealth = async () => {
    const response = await fetch("/api/v1/health");
    return response.json();
};

export const loginOfficer = async (officerId, password) => {
    const response = await fetch("/api/v1/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ officer_id: officerId, password: password }),
    });

    if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Invalid Officer ID or Password");
    }

    return response.json();
};
