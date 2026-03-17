"""Entry point: python -m radar_sim starts the WebSocket server."""

import uvicorn


def main() -> None:
    uvicorn.run("radar_sim.api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
