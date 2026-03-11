'use client'

import React, { useState } from 'react'

interface SuccessMessageProps {
  ticketId: string
  onReset: () => void
}

function SuccessMessage({ ticketId, onReset }: SuccessMessageProps) {
  const [copied, setCopied] = useState(false)

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(ticketId)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-lg p-8 text-center">
      {/* Success Icon */}
      <div className="flex justify-center mb-6">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      </div>

      {/* Success Message */}
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Request Submitted!</h2>
      <p className="text-gray-600 mb-6">
        We'll respond to your email within 5 minutes
      </p>

      {/* Ticket ID */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-500 mb-2">Your Ticket ID</p>
        <div 
          className="flex items-center justify-center space-x-2 cursor-pointer hover:bg-gray-100 rounded p-2 transition-colors"
          onClick={copyToClipboard}
        >
          <code className="text-lg font-mono text-gray-900">{ticketId}</code>
          <button className="text-gray-400 hover:text-gray-600">
            {copied ? (
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            )}
          </button>
        </div>
        {copied && (
          <p className="text-sm text-green-600 mt-2">Copied!</p>
        )}
      </div>

      {/* Action Links */}
      <div className="space-y-4">
        <a 
          href={`/ticket/${ticketId}`}
          className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
        >
          Check ticket status
          <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </a>
        
        <button
          onClick={onReset}
          className="block w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
        >
          Submit another request
        </button>
      </div>
    </div>
  )
}

export default SuccessMessage
