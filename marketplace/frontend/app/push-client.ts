// TEMPORARY STUB: the phone-app agent owns the real module. Replace with theirs.
export type PushState = "unsupported" | "needs-install" | "denied" | "off" | "on";
export async function getPushState(): Promise<PushState> { return "unsupported"; }
export async function enablePush(): Promise<"on" | "denied" | "unsupported" | "needs-install"> { return "unsupported"; }
export async function disablePush(): Promise<void> {}
