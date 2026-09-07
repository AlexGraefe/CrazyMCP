# CrazyMCP

A demo project that uses an LLM to control a swarm of Crazyflie quadcopters.

You need two PCs for this. One to run the frontend and the GPU PC that runs the LLM.
Your local PC needs to be connected to a Crazyflie 2 Radio.

Connect to the GPU PC:

```bash
ssh ssh <account name>@<ip address of GPU PC> 
```

## Installation

Clone this repo (both on the GPU PC and the local PC):

```bash
git clone https://github.com/AlexGraefe/CrazyMCP.git
cd CrazyMCP
```

### 1. Install `uv`

On Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal if necessary, then verify the installation:

```bash
uv --version
```

In case it is not found, do the following:

```bash
nano ~/.bashrc
```

At the end of the file add:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

Restart your terminal.


### 2. Create the virtual environment

From the project directory, create a virtual environment with Python 3.13:

```bash
uv venv --python 3.13
```

`uv` will install Python 3.13 automatically if it is not already available.

### 3. Install the dependencies

Install the dependencies recorded in `uv.lock`:

```bash
uv sync
```

To activate the virtual environment, run:

```bash
source .venv/bin/activate
```


## How to run the repo:

Turn on the four drones.

On the GPU PC, run:
```bash
vllm serve Qwen/Qwen3.6-27B --port 8000 --tensor-parallel-size 1 --max-model-len 128000 --reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder --quantization bitsandbytes --max_num_seqs 1
```

It will take a while till it launches, especially, when run for the first time as it needs to download the LLM.

On the other PC, run (replace the ip with the GPUS ip):
```bash
uv run python main.py --gpu-ip 192.168.1.100 --gpu-port 8001
```

