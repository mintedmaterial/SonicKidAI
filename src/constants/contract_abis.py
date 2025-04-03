"""Contract ABIs for interacting with EternalAI smart contracts"""

AGENT_ABI = [
    {
        "inputs": [],
        "name": "getSystemPrompt",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "getPromptSchedulerAddress",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes", "name": "prompt", "type": "bytes"}],
        "name": "prompt",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

WORKER_HUB_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "inferenceId", "type": "uint256"}],
        "name": "getAssignmentsByInference",
        "outputs": [{"internalType": "uint256[]", "name": "", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "assignmentId", "type": "uint256"}],
        "name": "getAssignmentInfo",
        "outputs": [
            {"internalType": "uint256", "name": "inferenceId", "type": "uint256"},
            {"internalType": "address", "name": "worker", "type": "address"},
            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
            {"internalType": "uint256", "name": "status", "type": "uint256"},
            {"internalType": "bytes", "name": "proof", "type": "bytes"},
            {"internalType": "bytes", "name": "commitment", "type": "bytes"},
            {"internalType": "bytes", "name": "output", "type": "bytes"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "inferenceId", "type": "uint256"},
            {"indexed": True, "name": "worker", "type": "address"}
        ],
        "name": "NewInference",
        "type": "event"
    }
]

PROMPT_SCHEDULER_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "inferenceId", "type": "uint256"}],
        "name": "getInferenceInfo",
        "outputs": [
            {"internalType": "uint256", "name": "id", "type": "uint256"},
            {"internalType": "address", "name": "requester", "type": "address"},
            {"internalType": "uint256", "name": "modelId", "type": "uint256"},
            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
            {"internalType": "uint256", "name": "status", "type": "uint256"},
            {"internalType": "uint256", "name": "round", "type": "uint256"},
            {"internalType": "bytes", "name": "input", "type": "bytes"},
            {"internalType": "bytes", "name": "proof", "type": "bytes"},
            {"internalType": "bytes", "name": "commitment", "type": "bytes"},
            {"internalType": "bytes", "name": "output", "type": "bytes"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

HYBRID_MODEL_ABI = [
    {
        "inputs": [
            {"internalType": "bytes", "name": "prompt", "type": "bytes"},
            {"internalType": "bool", "name": "immediate", "type": "bool"}
        ],
        "name": "infer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]
