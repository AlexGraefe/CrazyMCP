import argparse
import asyncio
import sys

from langchain.tools import tool
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, LoadingIndicator, Static

from agent import create_agent
from runner.swarm_runner import run_swarm_show

_captured = {"swarm_show_func": None}


@tool(parse_docstring=True)
def swarm_show_execute(swarm_show_func: str) -> str:
    """Execute a swarm show by generating and running a complete script.

    Args:
        swarm_show_func: Python function code for swarm_show(current_time: float).

    Returns:
        Result message with exit code and captured output.
    """
    _captured["swarm_show_func"] = swarm_show_func
    return "Code captured. Will run after LLM finishes."


class SwarmApp(App):
    CSS = """
    #output {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
        border: solid $primary;
    }
    #input-area {
        height: auto;
        dock: bottom;
        padding: 1 2;
    }
    #input-area:disabled {
        opacity: 0.5;
    }
    #input-widget {
        width: 100%;
    }
    LoadingIndicator {
        height: 1;
        dock: bottom;
    }
    """

    def __init__(self, simulate: bool, address_offset: int, **kwargs):
        super().__init__(**kwargs)
        self.simulate = simulate
        self.address_offset = address_offset
        self._output_text = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="output")
        yield Vertical(
            Input(placeholder="Enter prompt...", id="input-widget"),
            id="input-area",
        )
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        input_area = self.query_one("#input-area")
        input_widget = self.query_one("#input-widget", Input)
        input_area.disabled = True
        input_widget.value = ""
        self._append(f"> {prompt}\n")
        loading = LoadingIndicator()
        self.mount(loading)
        self._run_agent(prompt, loading)

    def _append(self, text: str) -> None:
        self._output_text += text
        output = self.query_one("#output", Static)
        output.update(self._output_text)
        self.call_after_refresh(self._scroll_output)

    def _scroll_output(self) -> None:
        output = self.query_one("#output", Static)
        output.scroll_end(animate=False)

    def _finish_run(self, loading: LoadingIndicator) -> None:
        loading.remove()
        self.query_one("#input-area").disabled = False
        self.query_one("#input-widget", Input).focus()

    @work(exclusive=True, thread=True)
    def _run_agent(self, prompt: str, loading: LoadingIndicator) -> None:
        _captured["swarm_show_func"] = None

        agent = create_agent(tools=[swarm_show_execute])

        stream = agent.stream_events(
            {"messages": [{"role": "user", "content": prompt}]},
            version="v3",
        )
        for message in stream.messages:
            for token in message.reasoning:
                self.call_from_thread(self._append, f"[thinking] {token}")
            for token in message.text:
                self.call_from_thread(self._append, token)
        self.call_from_thread(self._append, "\n")

        swarm_show_func = _captured["swarm_show_func"]
        if swarm_show_func is None:
            self.call_from_thread(self._append, "LLM did not generate a swarm show function.\n")
            self.call_from_thread(self._finish_run, loading)
            return

        self.call_from_thread(self._append, "--- Generated swarm_show function ---\n")
        self.call_from_thread(self._append, swarm_show_func)
        self.call_from_thread(self._append, "\n-------------------------------------\n")

        self.call_from_thread(self._append, "Running experiment...\n")
        exit_code, stdout, stderr = asyncio.run(
            run_swarm_show(
                swarm_show_func,
                num_drones=3,
                simulated=self.simulate,
                no_wait=False,
                address_offset=self.address_offset,
            )
        )
        if stdout:
            self.call_from_thread(self._append, stdout + "\n")
        if stderr:
            self.call_from_thread(self._append, stderr + "\n")
        self.call_from_thread(self._append, f"Exit code: {exit_code}\n")

        self.call_from_thread(self._finish_run, loading)


def run() -> None:
    parser = argparse.ArgumentParser(description="Crazyflie Swarm Control")
    parser.add_argument(
        "--address-offset",
        type=int,
        default=0,
        metavar="N",
        help="Offset added to drone address indices",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode",
    )
    args = parser.parse_args()

    app = SwarmApp(simulate=args.simulate, address_offset=args.address_offset)
    app.run()


if __name__ == "__main__":
    run()
