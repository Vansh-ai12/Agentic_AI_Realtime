"use client";

import Link from "next/link";
import {
  PageHeader,
  Card,
  Button,
} from "@/components/ui";

export default function ConnectPage() {
  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <PageHeader
        badgeText="Data Source Connections"
        title="Connect Your Data Sources"
        description="Link your Gmail and Notion accounts to enable intelligent document ingestion and semantic search across your personal knowledge base."
        actions={
          <Button href="/" variant="secondary" size="md">
            &larr; Back to Dashboard
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gmail Card */}
        <Card>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                <span className="text-white text-xl font-bold">G</span>
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Gmail</h3>
                <p className="text-xs text-slate-400">Email & conversation history</p>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-400">
              <p>Sync your Gmail emails to enable intelligent search across your conversations and attachments.</p>
              <ul className="space-y-1 ml-2">
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Email threads and metadata</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Attachments and documents</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Real-time sync</span>
                </li>
              </ul>
            </div>

            <Button href="/connect/gmail" variant="primary" size="md" className="w-full">
              Connect Gmail
            </Button>
          </div>
        </Card>

        {/* Notion Card */}
        <Card>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-slate-700 to-slate-900 flex items-center justify-center border border-slate-600">
                <span className="text-white text-xl font-bold">N</span>
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Notion</h3>
                <p className="text-xs text-slate-400">Pages, databases & docs</p>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-400">
              <p>Index your Notion workspace to search across pages, databases, and collaborative content.</p>
              <ul className="space-y-1 ml-2">
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Pages and sub-pages</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Databases and structured data</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="text-emerald-400">✓</span>
                  <span>Rich text and formatting</span>
                </li>
              </ul>
            </div>

            <Button href="/connect/notion" variant="primary" size="md" className="w-full">
              Connect Notion
            </Button>
          </div>
        </Card>
      </div>

      {/* Security Notice */}
      <Card>
        <div className="flex items-start gap-3">
          <span className="text-indigo-400 text-lg">🔒</span>
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-indigo-300">Security & Privacy</h4>
            <p className="text-xs text-slate-400 leading-relaxed">
              All connections use OAuth 2.0 for secure authentication. Your data is encrypted at rest and in transit. 
              We never store your passwords and you can revoke access at any time. Connection tokens are stored securely 
              and only used to sync data you explicitly authorize.
            </p>
          </div>
        </div>
      </Card>
    </main>
  );
}
