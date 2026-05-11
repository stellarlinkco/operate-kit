from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from operatekit.core.observation.observation import ObservationKind
from operatekit.core.observation.snapshot import ObservationSnapshot
from operatekit.core.target.target import TargetSpec
from operatekit.core.ui.locator import Locator
from operatekit.core.workflow.step import Step
from operatekit.plugins.storage.jsonl import JsonlObservationRepository
from operatekit.ports.host_driver import HostDriver
from operatekit.ports.surface_driver import SurfaceDriver
from operatekit.rpa.flow_compiler import FlowCompiler
from operatekit.rpa.screen_object import ScreenObject, screen_from_spec
from operatekit.runtime.context import RunContext
from operatekit.runtime.ledger import JsonlRunLedger
from operatekit.runtime.notifier import JsonlNotifier
from operatekit.runtime.runner import WorkflowRunner
from operatekit.runtime.tracing import TraceConfig, TraceRecorder


class AutomationSDK:
    def __init__(
        self,
        *,
        target: TargetSpec,
        surface: SurfaceDriver,
        host: HostDriver | None = None,
        artifacts_dir: str | Path = "./artifacts",
    ):
        self.target = target
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.observations = JsonlObservationRepository(self.artifacts_dir / "observations.jsonl")
        self.ledger = JsonlRunLedger(self.artifacts_dir / "runs.jsonl")
        self.notifier = JsonlNotifier(self.artifacts_dir / "events.jsonl")
        self.context = RunContext(
            target=target,
            host=host,
            surface=surface,
            observations=self.observations,
            artifacts_dir=self.artifacts_dir,
            notifier=self.notifier,
        )
        self.runner = WorkflowRunner(self.ledger)
        self.flow_compiler = FlowCompiler()

    @classmethod
    def create_android(
        cls,
        *,
        package: str,
        serial: str | None = None,
        artifacts_dir: str | Path = "./artifacts",
    ) -> "AutomationSDK":
        from operatekit.plugins.android.adbutils_host import AdbutilsHostDriver
        from operatekit.plugins.android.uiautomator2_surface import Uiautomator2SurfaceDriver

        target = TargetSpec.android(package, serial=serial)
        host = AdbutilsHostDriver(serial=serial)
        surface = Uiautomator2SurfaceDriver(serial=serial, package=package)
        return cls(target=target, host=host, surface=surface, artifacts_dir=artifacts_dir)

    @classmethod
    def create_windows(
        cls,
        *,
        executable: str | None = None,
        title: str | None = None,
        backend: str = "uia",
        launch_args: list[str] | None = None,
        artifacts_dir: str | Path = "./artifacts",
        connect: bool = False,
    ) -> "AutomationSDK":
        from operatekit.plugins.windows.pywinauto_host import LocalWindowsHostDriver
        from operatekit.plugins.windows.pywinauto_surface import PywinautoSurfaceDriver

        target = TargetSpec.windows(executable=executable, title=title, backend=backend, launch_args=launch_args)
        host = LocalWindowsHostDriver()
        surface = PywinautoSurfaceDriver(executable=executable, title=title, backend=backend, launch_args=launch_args, connect=connect)
        return cls(target=target, host=host, surface=surface, artifacts_dir=artifacts_dir)

    @classmethod
    def create_with_drivers(
        cls,
        *,
        target: TargetSpec,
        surface: SurfaceDriver,
        host: HostDriver | None = None,
        artifacts_dir: str | Path = "./artifacts",
    ) -> "AutomationSDK":
        return cls(target=target, surface=surface, host=host, artifacts_dir=artifacts_dir)

    def enable_trace(self, config: TraceConfig | None = None) -> TraceRecorder:
        recorder = TraceRecorder(self.artifacts_dir, config=config)
        self.context.trace = recorder
        return recorder

    def run_steps(self, name: str, steps: Iterable[Step], *, raise_on_failure: bool = True):
        return self.runner.run_steps(name, list(steps), self.context, raise_on_failure=raise_on_failure)

    def run_flow_spec(self, flow: dict[str, Any], *, raise_on_failure: bool = True):
        steps = self.flow_compiler.compile(flow)
        return self.run_steps(flow.get("name", "flow"), steps, raise_on_failure=raise_on_failure)

    def screen(self, name: str, elements: dict[str, dict[str, Any]]) -> ScreenObject:
        return screen_from_spec(name, elements)

    def snapshot_observation(self, store_key: str, *, fields: list[str] | None = None) -> ObservationSnapshot:
        obs = self.context.get(store_key)
        if obs is None:
            raise KeyError(store_key)
        snapshot = ObservationSnapshot.from_observation(obs, fields=fields)
        self.context.set(f"{store_key}_snapshot", snapshot)
        return snapshot

    def mitm_proxy(self, *, port: int = 8080, host: str = "127.0.0.1", endpoint_patterns: list[str] | None = None):
        from operatekit.plugins.capture.mitmproxy.proxy import MitmproxyCaptureProxy
        return MitmproxyCaptureProxy(
            repo_path=self.artifacts_dir / "observations.jsonl",
            port=port,
            host=host,
            endpoint_patterns=endpoint_patterns or [],
        )

    def android_mitm_session(
        self,
        *,
        port: int = 8080,
        route: str = "adb_reverse",
        endpoint_patterns: list[str] | None = None,
        lan_host: str | None = None,
    ):
        from operatekit.plugins.android.adbutils_host import AdbutilsHostDriver
        from operatekit.plugins.android.proxy_controller import AndroidProxyController
        from operatekit.plugins.capture.mitmproxy.proxy import MitmproxyCaptureProxy
        from operatekit.plugins.capture.mitmproxy.session import MitmCaptureSession

        if not isinstance(self.context.host, AdbutilsHostDriver):
            raise TypeError("android_mitm_session requires an Android AdbutilsHostDriver")
        proxy = MitmproxyCaptureProxy(
            repo_path=self.artifacts_dir / "observations.jsonl",
            port=port,
            endpoint_patterns=endpoint_patterns or [],
        )
        device_proxy = AndroidProxyController(self.context.host, port=port, route=route, lan_host=lan_host)
        return MitmCaptureSession(proxy=proxy, device_proxy=device_proxy)
