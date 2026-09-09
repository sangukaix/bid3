import { API_BASE_URL } from "@/lib/api";

export type BidSyncState = {
  status: "idle" | "syncing" | "success" | "error";
  message: string;
};

type BidSyncListener = (state: BidSyncState) => void;

let syncState: BidSyncState = { status: "idle", message: "" };
let syncPromise: Promise<void> | null = null;
const listeners = new Set<BidSyncListener>();

function updateSyncState(nextState: BidSyncState) {
  syncState = nextState;
  listeners.forEach((listener) => listener(syncState));
}

export function getBidSyncState() {
  return syncState;
}

export function subscribeBidSync(listener: BidSyncListener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function startBidSync(token: string) {
  if (syncPromise) return syncPromise;

  updateSyncState({ status: "syncing", message: "" });
  syncPromise = fetch(`${API_BASE_URL}/api/bids/sync/`, {
    method: "POST",
    headers: { Authorization: `Token ${token}` },
  })
    .then((response) => {
      if (!response.ok) throw new Error();
      updateSyncState({ status: "success", message: "" });
    })
    .catch(() => {
      updateSyncState({
        status: "error",
        message: "공고 업데이트에 실패했습니다. 잠시 후 다시 시도해 주세요.",
      });
    })
    .finally(() => {
      syncPromise = null;
    });

  return syncPromise;
}
