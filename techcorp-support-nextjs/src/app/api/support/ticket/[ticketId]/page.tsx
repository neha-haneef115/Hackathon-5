'use client'

import React, { useState, useEffect } from 'react'

interface TicketData {
  ticket_id: string
  status: string
  subject: string
  category: string
  priority: string
  created_at: string
  messages: Array<{
    content: string
    role: string
    created_at: string
  }>
}

export default function TicketStatusPage({ params }: { params: { ticketId: string } }) {
  const [ticketData, setTicketData] = useState<TicketData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchTicketStatus()
  }, [params.ticketId])

  const fetchTicketStatus = async () => {
    try {
      const response = await fetch(`/api/support/ticket/${params.ticketId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch ticket status')
      }
      const data = await response.json()
      setTicketData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading ticket status...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Error</h1>
          <p className="text-gray-600 mb-4">{error}</p>
          <a 
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
          >
            Back to Support Form
            <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </a>
        </div>
      </div>
    )
  }

  if (!ticketData) {
    return null
  }

  const statusColors = {
    open: 'bg-blue-100 text-blue-800',
    processing: 'bg-yellow-100 text-yellow-800',
    resolved: 'bg-green-100 text-green-800',
    escalated: 'bg-orange-100 text-orange-800'
  }

  const priorityColors = {
    low: 'bg-gray-100 text-gray-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800'
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <a 
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium mb-4"
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Support Form
          </a>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Ticket Status</h1>
          <p className="text-gray-600">Track your support request progress</p>
        </div>

        {/* Ticket Information */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Ticket Details</h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Ticket ID</dt>
                  <dd className="mt-1 font-mono text-sm text-gray-900">{ticketData.ticket_id}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Subject</dt>
                  <dd className="mt-1 text-gray-900">{ticketData.subject}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Category</dt>
                  <dd className="mt-1 text-gray-900">{ticketData.category}</dd>
                </div>
              </dl>
            </div>
            
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Status & Priority</h2>
              <dl className="space-y-3">
                <div>
                  <dt className="text-sm font-medium text-gray-500">Status</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[ticketData.status as keyof typeof statusColors] || 'bg-gray-100 text-gray-800'}`}>
                      {ticketData.status}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Priority</dt>
                  <dd className="mt-1">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${priorityColors[ticketData.priority as keyof typeof priorityColors] || 'bg-gray-100 text-gray-800'}`}>
                      {ticketData.priority}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="mt-1 text-gray-900">
                    {new Date(ticketData.created_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>

        {/* Messages */}
        {ticketData.messages && ticketData.messages.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Conversation</h2>
            <div className="space-y-4">
              {ticketData.messages.map((message, index) => (
                <div 
                  key={index} 
                  className={`p-4 rounded-lg ${
                    message.role === 'customer' 
                      ? 'bg-gray-50 border-l-4 border-gray-300' 
                      : 'bg-blue-50 border-l-4 border-blue-300'
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium text-gray-900">
                      {message.role === 'customer' ? 'You' : 'Support Agent'}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(message.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-gray-700 whitespace-pre-wrap">{message.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
