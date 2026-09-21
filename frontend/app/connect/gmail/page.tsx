"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  PageHeader,
  Card,
  Button,
  LoadingState,
  ErrorState,
  GradientBanner,
} from "@/components/ui";

const API_BASE = "http://localhost:8000/api";

function GmailConnectionContent() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const searchParams = useSearchParams();

  useEffect(() => {
    // Check if user was just redirected from OAuth callback
    if (searchParams.get("connected") === "true") {
      setConnected(true);
      setCheckingStatus(false);
    } else {
      checkConnectionStatus();
    }
  }, [searchParams]);

  const checkConnectionStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/connections`);
      const data = await response.json();
      const gmailConnection = data.connections?.find((c: any) => c.source === "gmail");
      setConnected(!!gmailConnection);
    } catch (err) {
      console.error("Failed to check connection status:", err);
    } finally {
      setCheckingStatus(false);
    }
  };

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Redirect to backend OAuth endpoint
      window.location.href = "http://localhost:8000/api/auth/gmail";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connection failed");
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/connections/gmail`, {
        method: "DELETE"
      });
      if (response.ok) {
        setConnected(false);
      } else {
        throw new Error("Failed to disconnect");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Disconnection failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <PageHeader
        badgeText="Data Source Connection"
        title="Connect Gmail"
        description="Securely link your Gmail account to enable real-time email ingestion and intelligent document retrieval."
        actions={
          <Button href="/" variant="secondary" size="md">
            &larr; Back to Dashboard
          </Button>
        }
      />

      <GradientBanner variant="indigo">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center shrink-0">
            <span className="text-white text-lg font-bold">G</span>
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-white">Gmail Integration</h3>
            <p className="text-xs text-slate-300">
              Sync your emails to enable intelligent search across your conversations and attachments with semantic understanding.
            </p>
          </div>
        </div>
      </GradientBanner>

      <Card>
        <div className="space-y-6">
          {/* Connection Status */}
          <div className="flex items-center justify-between p-4 bg-slate-900/60 rounded-lg border border-slate-800">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${connected ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-slate-600'} ${connected ? 'animate-pulse' : ''}`} />
              <span className="text-sm font-medium text-slate-200">
                {connected ? 'Connected' : 'Not Connected'}
              </span>
            </div>
            {connected && (
              <span className="text-xs text-slate-500 font-mono">
                Last sync: Just now
              </span>
            )}
          </div>

          {/* Connection Info */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white">What will be synced:</h3>
            <ul className="space-y-2 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <span className="text-indigo-400">•</span>
                <span>Email threads and conversation history</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-400">•</span>
                <span>Attachments and document references</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-400">•</span>
                <span>Sender and recipient metadata</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-400">•</span>
                <span>Subject lines and thread organization</span>
              </li>
            </ul>
          </div>

          {/* Security Notice */}
          <div className="p-4 bg-indigo-950/30 border border-indigo-500/30 rounded-lg">
            <div className="flex items-start gap-3">
              <span className="text-indigo-400 text-lg">🔒</span>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-indigo-300">Security & Privacy</h4>
                <p className="text-xs text-slate-400">
                  Your Gmail data is encrypted at rest and in transit. We use OAuth 2.0 for secure authentication and never store your Gmail password. Access can be revoked at any time.
                </p>
              </div>
            </div>
          </div>

          {/* Action Button */}
          {checkingStatus && <LoadingState message="Checking connection status..." />}
          {loading && <LoadingState message={connected ? "Disconnecting..." : "Connecting to Gmail..."} />}
          {error && <ErrorState title="Connection Failed" error={error} />}
          
          {!checkingStatus && !loading && !error && (
            <div className="flex gap-3">
              {!connected ? (
                <Button 
                  onClick={handleConnect}
                  variant="primary" 
                  size="md"
                  className="flex-1"
                >
                  Connect Gmail Account
                </Button>
              ) : (
                <div className="flex gap-3 w-full">
                  <Button variant="secondary" size="md" className="flex-1">
                    Sync Now
                  </Button>
                  <Button 
                    onClick={handleDisconnect}
                    variant="danger" 
                    size="md" 
                    className="flex-1"
                  >
                    Disconnect
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Usage Stats (when connected) */}
      {connected && (
        <Card>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800">
              <div className="text-[11px] text-slate-500 font-mono">Emails Indexed</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">1,247</div>
            </div>
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800">
              <div className="text-[11px] text-slate-500 font-mono">Chunks Created</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">3,891</div>
            </div>
            <div className="p-4 bg-slate-900/60 rounded-lg border border-slate-800">
              <div className="text-[11px] text-slate-500 font-mono">Last Sync</div>
              <div className="text-2xl font-bold font-mono text-white mt-1">2m ago</div>
            </div>
          </div>
        </Card>
      )}
    </main>
  );
}

export default function GmailConnectionPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading connection page..." />}>
      <GmailConnectionContent />
    </Suspense>
  );
}
