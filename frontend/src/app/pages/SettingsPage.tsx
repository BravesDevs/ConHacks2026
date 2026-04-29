import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ArrowLeft, Bell, Lock, User, CreditCard, LogOut } from 'lucide-react';


export default function SettingsPage() {
  const navigate = useNavigate();


  const [activeTab, setActiveTab] = useState('profile');

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'billing', label: 'Billing', icon: CreditCard },
  ];

  return (
    <div className="min-h-screen bg-[#F5F5F2] dark:bg-gray-900">
      <nav className="border-b border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 px-8 py-4">
        <div className="mx-auto flex max-w-7xl items-center gap-4">
          <button
            onClick={() => navigate('/')}
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/10 dark:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[#1D9E75]" />
            <span className="font-medium dark:text-white">InfraLens</span>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-7xl px-8 py-8">
        <div className="mb-8 flex items-center justify-between">
          <h1 className="text-3xl dark:text-white">Settings</h1>
        </div>

        <div className="grid grid-cols-[240px_1fr] gap-6">
          <div className="flex flex-col justify-between h-full">
            <div className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex w-full items-center gap-3 rounded-lg px-4 py-2.5 text-left transition-colors ${
                      activeTab === tab.id
                        ? 'bg-[#1D9E75]/10 text-[#1D9E75]'
                        : 'text-black/60 dark:text-white/60 hover:bg-black/5 dark:hover:bg-white/5'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="text-sm">{tab.label}</span>
                  </button>
                );
              })}
            </div>

          </div>

          <div className="rounded-2xl border border-black/10 dark:border-white/10 bg-white dark:bg-gray-800 p-8">
            {activeTab === 'profile' && (
              <div>
                <h2 className="mb-6 text-xl dark:text-white">Profile settings</h2>
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                        First name
                      </label>
                      <input
                        type="text"
                        placeholder="John"
                        className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                      />
                    </div>
                    <div>
                      <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                        Last name
                      </label>
                      <input
                        type="text"
                        placeholder="Doe"
                        className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                      Email address
                    </label>
                    <input
                      type="email"
                      value="john@company.com"
                      readOnly
                      className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-4 py-2.5 text-black/60 dark:text-white/60 outline-none cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                      Company
                    </label>
                    <input
                      type="text"
                      value="Acme Corp"
                      readOnly
                      className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5 px-4 py-2.5 text-black/60 dark:text-white/60 outline-none cursor-not-allowed"
                    />
                  </div>
                  <div className="flex justify-end gap-3 border-t border-black/10 dark:border-white/10 pt-6">
                    <button className="rounded-lg px-5 py-2.5 text-black/60 dark:text-white/60 transition-colors hover:bg-black/5 dark:hover:bg-white/5">
                      Cancel
                    </button>
                    <button className="rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90">
                      Save changes
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div>
                <h2 className="mb-6 text-xl dark:text-white">Notification preferences</h2>
                <div className="space-y-4">
                  {[
                    { label: 'Cost alerts', description: 'Get notified when spending exceeds threshold' },
                    { label: 'Weekly reports', description: 'Receive weekly cost optimization summaries' },
                    { label: 'Scan completion', description: 'Alert when infrastructure scans complete' },
                    { label: 'New recommendations', description: 'Notify when AI finds optimization opportunities' },
                  ].map((item, index) => (
                    <div key={index} className="flex items-center justify-between border-b border-black/10 dark:border-white/10 pb-4 last:border-0">
                      <div>
                        <div className="font-medium dark:text-white">{item.label}</div>
                        <div className="text-sm text-black/60 dark:text-white/60">{item.description}</div>
                      </div>
                      <label className="relative inline-flex cursor-pointer items-center">
                        <input type="checkbox" className="peer sr-only" defaultChecked={index < 2} />
                        <div className="peer h-6 w-11 rounded-full bg-black/10 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:transition-all peer-checked:bg-[#1D9E75] peer-checked:after:translate-x-full"></div>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div>
                <h2 className="mb-6 text-xl dark:text-white">Security settings</h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="mb-4 font-medium dark:text-white">Change password</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                          Current password
                        </label>
                        <input
                          type="password"
                          placeholder="••••••••"
                          className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                          New password
                        </label>
                        <input
                          type="password"
                          placeholder="••••••••"
                          className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-sm text-black/80 dark:text-white/80">
                          Confirm new password
                        </label>
                        <input
                          type="password"
                          placeholder="••••••••"
                          className="w-full rounded-lg border border-black/10 dark:border-white/10 bg-white dark:bg-gray-700 dark:text-white px-4 py-2.5 outline-none transition-colors focus:border-[#1D9E75]"
                        />
                      </div>
                      <button className="rounded-lg bg-[#1D9E75] px-5 py-2.5 text-white transition-opacity hover:opacity-90">
                        Update password
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'billing' && (
              <div>
                <h2 className="mb-6 text-xl dark:text-white">Billing & subscription</h2>
                <div className="space-y-6">
                  <div className="rounded-lg border border-black/10 dark:border-white/10 bg-[#1D9E75]/5 p-4">
                    <div className="mb-2 text-sm text-black/60 dark:text-white/60">Current plan</div>
                    <div className="mb-1 text-2xl dark:text-white">Pro Plan</div>
                    <div className="text-sm text-black/60 dark:text-white/60">$49/month · Billed monthly</div>
                  </div>
                  <div>
                    <h3 className="mb-4 font-medium dark:text-white">Payment method</h3>
                    <div className="flex items-center justify-between rounded-lg border border-black/10 dark:border-white/10 p-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-14 items-center justify-center rounded bg-black/5 dark:bg-white/5">
                          <CreditCard className="h-5 w-5 text-black/40 dark:text-white/40" />
                        </div>
                        <div>
                          <div className="font-medium dark:text-white">•••• •••• •••• 4242</div>
                          <div className="text-sm text-black/60 dark:text-white/60">Expires 12/27</div>
                        </div>
                      </div>
                      <button className="rounded-lg border border-black/10 dark:border-white/10 px-4 py-2 text-sm dark:text-white transition-colors hover:bg-black/5 dark:hover:bg-white/5">
                        Update
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
