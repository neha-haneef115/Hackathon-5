import React, { useState, useEffect } from 'react'

function TicketStatus({ ticketId }) {
  const [ticket, setTicket] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchTicketStatus = async () => {
    try {
      const response = await fetch(`/api/support/ticket/${ticketId}`)
      if (!response.ok) {
        if (response.status === 404) {
          setError('Ticket not found')
        } else {
          setError('Failed to load ticket status')
        }
        return
      }
      const data = await response.json()
      setTicket(data)
      setError(null)
    } catch (err) {
      setError('Network error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTicketStatus()
    
    // Poll every 15 seconds
    const interval = setInterval(fetchTicketStatus, 15000)
    
    return () => clearInterval(interval)
  }, [ticketId])

  const getStatusColor = (status) => {
    switch (status) {
      case 'open': return 'status-badge.open'
      case 'processing': return 'status-badge.processing'
      case 'resolved': return 'status-badge.resolved'
      case 'escalated': return 'status-badge.escalated'
      default: return 'status-badge.open'
    }
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString()
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-lg p-8">
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600">{error}</p>
        </div>
      </div>
    )
  }

  if (!ticket) {
    return null
  }

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-lg p-8">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Ticket Status</h1>
            <p className="text-gray-600 mt-1">Ticket ID: {ticketId}</p>
          </div>
          <span className={`status-badge ${getStatusColor(ticket.status)}`}>
            {ticket.status.charAt(0).toUpperCase() + ticket.status.slice(1)}
          </span>
        </div>
        <div className="mt-4">
          <p className="text-sm text-gray-500">
            Created: {formatTimestamp(ticket.created_at)}
          </p>
          <p className="text-sm text-gray-500">
            Subject: {ticket.subject}
          </p>
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Conversation</h3>
        
        {ticket.messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === 'customer' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-lg rounded-lg px-4 py-3 ${
                message.role === 'customer'
                  ? 'bg-primary-100 text-primary-900'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-xs font-medium">
                  {message.role === 'customer' ? 'You' : 'TechCorp Support'}
                </span>
                <span className="text-xs opacity-75">
                  {formatTimestamp(message.created_at)}
                </span>
              </div>
              <div className="text-sm whitespace-pre-wrap">
                {message.content}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Refresh Button */}
      <div className="mt-6 text-center">
        <button
          onClick={fetchTicketStatus}
          className="text-primary-600 hover:text-primary-700 text-sm font-medium"
        >
          Refresh status
        </button>
      </div>
    </div>
  )
}

export default TicketStatus
