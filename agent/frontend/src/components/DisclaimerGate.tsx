import { useEffect, useState, type ReactNode } from "react";

import { fetchDisclaimerStatus } from "../api/agentApi";
import { DisclaimerModal } from "./DisclaimerModal";

export const DISCLAIMER_STORAGE_KEY = "agent_disclaimer_accepted_v1";

interface DisclaimerGateProps {
  children: ReactNode;
}

export function DisclaimerGate({ children }: DisclaimerGateProps) {
  const [checking, setChecking] = useState(true);
  const [accepted, setAccepted] = useState(
    () => window.localStorage.getItem(DISCLAIMER_STORAGE_KEY) === "1",
  );

  useEffect(() => {
    let cancelled = false;

    void fetchDisclaimerStatus()
      .then(({ accepted: isAccepted }) => {
        if (cancelled) return;
        if (isAccepted) {
          window.localStorage.setItem(DISCLAIMER_STORAGE_KEY, "1");
          setAccepted(true);
        } else {
          window.localStorage.removeItem(DISCLAIMER_STORAGE_KEY);
          setAccepted(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          window.localStorage.removeItem(DISCLAIMER_STORAGE_KEY);
          setAccepted(false);
        }
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const handleAccepted = () => {
    window.localStorage.setItem(DISCLAIMER_STORAGE_KEY, "1");
    setAccepted(true);
  };

  if (checking && !accepted) {
    return (
      <div className="flex h-dvh items-center justify-center text-sm text-gray-400">
        Loading…
      </div>
    );
  }

  return (
    <>
      {children}
      {!accepted ? <DisclaimerModal onAccepted={handleAccepted} /> : null}
    </>
  );
}
