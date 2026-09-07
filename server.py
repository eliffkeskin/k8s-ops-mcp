from mcp.server.mcpserver import MCPServer
from kubernetes import client, config

config.load_kube_config(config_file="~/.kube/rke2-config")
v1 = client.CoreV1Api()
custom = client.CustomObjectsApi()

mcp = MCPServer("k8s-ops")

@mcp.tool()
def list_pods(namespace: str = "llm") -> str:
    """List pods in a namespace with status and restart counts."""
    pods = v1.list_namespaced_pod(namespace)
    lines = []
    for p in pods.items:
        restarts = sum(cs.restart_count for cs in (p.status.container_statuses or []))
        lines.append(f"{p.metadata.name}  {p.status.phase}  restarts={restarts}")
    return "\n".join(lines) or f"no pods in {namespace}"

@mcp.tool()
def get_events(namespace: str = "llm", warnings_only: bool = False) -> str:
    """Recent Kubernetes events in a namespace, deduplicated and sorted:
    warnings first, then normal events. Use warnings_only=True when diagnosing."""
    evs = v1.list_namespaced_event(namespace).items
    evs.sort(key=lambda e: (e.type != "Warning",
                            -(e.last_timestamp or e.event_time or datetime.min)
                             .timestamp() if (e.last_timestamp or e.event_time) else 0))
    lines = []
    for e in evs:
        if warnings_only and e.type != "Warning":
            continue
        obj = f"{e.involved_object.kind}/{e.involved_object.name}"
        count = f"(x{e.count}) " if (e.count or 1) > 1 else ""
        msg = " ".join((e.message or "").split())[:160]
        lines.append(f"[{e.type}] {count}{obj} — {e.reason}: {msg}")
    return "\n".join(lines[:30]) or f"no events in {namespace}"

@mcp.tool()
def describe_inference_services(namespace: str = "llm", name: str = "") -> str:
    """Describe KServe InferenceServices in a namespace: readiness, URLs, model spec, model status and failing conditions. Pass name to describe a single one."""
    if name:
        objs = [custom.get_namespaced_custom_object(
            "serving.kserve.io", "v1beta1", namespace, "inferenceservices", name)]
    else:
        objs = custom.list_namespaced_custom_object(
            "serving.kserve.io", "v1beta1", namespace, "inferenceservices")["items"]
    blocks = []
    for isvc in objs:
        meta, spec, status = isvc["metadata"], isvc.get("spec", {}), isvc.get("status", {})
        conds = {c["type"]: c for c in status.get("conditions", [])}
        ready = conds.get("Ready", {}).get("status", "Unknown")
        lines = [f"{meta['name']}  Ready={ready}  mode={status.get('deploymentMode', '-')}"]
        lines.append(f"  url: {status.get('url', '-')}")
        addr = status.get("address", {}).get("url")
        if addr:
            lines.append(f"  internal: {addr}")
        pred = spec.get("predictor", {})
        model = pred.get("model", {})
        if model:
            fmt = model.get("modelFormat", {}).get("name", "-")
            runtime = status.get("clusterServingRuntimeName") or model.get("runtime", "-")
            lines.append(f"  model: format={fmt} runtime={runtime} storageUri={model.get('storageUri', '-')}")
            env = {e["name"]: e.get("value", "") for e in model.get("env", [])}
            if env:
                lines.append("  env: " + " ".join(f"{k}={v}" for k, v in env.items()))
            res = model.get("resources", {})
            if res:
                lines.append(f"  resources: requests={res.get('requests', {})} limits={res.get('limits', {})}")
        if pred.get("minReplicas") is not None or pred.get("maxReplicas") is not None:
            lines.append(f"  replicas: min={pred.get('minReplicas', '-')} max={pred.get('maxReplicas', '-')}")
        ms = status.get("modelStatus", {})
        if ms:
            states, copies = ms.get("states", {}), ms.get("copies", {})
            lines.append(f"  modelStatus: active={states.get('activeModelState', '-')} target={states.get('targetModelState', '-')} "
                         f"transition={ms.get('transitionStatus', '-')} copies={copies.get('totalCopies', '-')} failed={copies.get('failedCopies', '-')}")
            if ms.get("lastFailureInfo"):
                lines.append(f"  lastFailure: {ms['lastFailureInfo']}")
        for c in status.get("conditions", []):
            if c["type"] == "Stopped" or c.get("status") == "True":
                continue
            lines.append(f"  condition {c['type']}={c['status']} {c.get('reason', '')}: {c.get('message', '')}".rstrip(": "))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) or f"no inferenceservices in {namespace}"

if __name__ == "__main__":
    mcp.run()
