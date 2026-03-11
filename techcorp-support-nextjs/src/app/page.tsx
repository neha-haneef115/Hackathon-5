import SupportForm from '@/components/SupportForm'

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            TechCorp Customer Support
          </h1>
          <p className="text-xl text-gray-600 mb-2">
            24/7 AI-powered customer support
          </p>
          <p className="text-lg text-gray-500">
            Get help with technical issues, billing questions, and more
          </p>
        </div>

        {/* Support Form */}
        <SupportForm />

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>© 2026 TechCorp. All rights reserved.</p>
          <p className="mt-2">
            Powered by AI • Response time: ~5 minutes
          </p>
        </div>
      </div>
    </div>
  );
}
