'use client'

import React, { useState } from 'react'
import SuccessMessage from './SuccessMessage'

interface FormData {
  name: string
  email: string
  subject: string
  category: string
  priority: string
  message: string
}

interface FormErrors {
  [key: string]: string
}

function SupportForm() {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    subject: '',
    category: 'general',
    priority: 'medium',
    message: ''
  })
  
  const [status, setStatus] = useState('idle') // idle, submitting, success, error
  const [ticketId, setTicketId] = useState('')
  const [error, setError] = useState('')
  const [charCount, setCharCount] = useState(0)

  const categories = [
    { value: 'general', label: 'General Question' },
    { value: 'technical', label: 'Technical Support' },
    { value: 'billing', label: 'Billing Inquiry' },
    { value: 'bug_report', label: 'Bug Report' },
    { value: 'feedback', label: 'Feedback' }
  ]

  const priorities = [
    { value: 'low', label: 'Low - Not urgent' },
    { value: 'medium', label: 'Medium - Need help soon' },
    { value: 'high', label: 'High - Urgent issue' }
  ]

  const validateForm = (): FormErrors => {
    const errors: FormErrors = {}
    
    if (formData.name.trim().length < 2) {
      errors.name = 'Name must be at least 2 characters'
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(formData.email)) {
      errors.email = 'Please enter a valid email address'
    }
    
    if (formData.subject.trim().length < 5) {
      errors.subject = 'Subject must be at least 5 characters'
    }
    
    if (formData.message.trim().length < 10) {
      errors.message = 'Message must be at least 10 characters'
    }
    
    if (formData.message.length > 1000) {
      errors.message = 'Message must be less than 1000 characters'
    }
    
    return errors
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    
    if (name === 'message') {
      setCharCount(value.length)
    }
    
    // Clear error for this field when user starts typing
    if (error) {
      setError('')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate form
    const errors = validateForm()
    if (Object.keys(errors).length > 0) {
      setError(errors[Object.keys(errors)[0]])
      return
    }
    
    setStatus('submitting')
    setError('')
    
    try {
      const response = await fetch('/api/support/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })
      
      if (!response.ok) {
        throw new Error('Failed to submit request')
      }
      
      const data = await response.json()
      setTicketId(data.ticket_id)
      setStatus('success')
    } catch (err) {
      setError('Failed to submit request. Please try again.')
      setStatus('error')
    }
  }

  const handleReset = () => {
    setFormData({
      name: '',
      email: '',
      subject: '',
      category: 'general',
      priority: 'medium',
      message: ''
    })
    setCharCount(0)
    setStatus('idle')
    setTicketId('')
    setError('')
  }

  if (status === 'success') {
    return <SuccessMessage ticketId={ticketId} onReset={handleReset} />
  }

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-2xl shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Contact Support</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name Field */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
            Name *
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-required="true"
            disabled={status === 'submitting'}
          />
          {error && error.includes('Name') && (
            <p className="text-red-600 text-sm mt-1">{error}</p>
          )}
        </div>

        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email *
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-required="true"
            disabled={status === 'submitting'}
          />
          {error && error.includes('email') && (
            <p className="text-red-600 text-sm mt-1">{error}</p>
          )}
        </div>

        {/* Subject Field */}
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
            Subject *
          </label>
          <input
            type="text"
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-required="true"
            disabled={status === 'submitting'}
          />
          {error && error.includes('Subject') && (
            <p className="text-red-600 text-sm mt-1">{error}</p>
          )}
        </div>

        {/* Category Field */}
        <div>
          <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
            Category
          </label>
          <select
            id="category"
            name="category"
            value={formData.category}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={status === 'submitting'}
          >
            {categories.map(cat => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        {/* Priority Field */}
        <div>
          <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
            Priority
          </label>
          <select
            id="priority"
            name="priority"
            value={formData.priority}
            onChange={handleInputChange}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={status === 'submitting'}
          >
            {priorities.map(pri => (
              <option key={pri.value} value={pri.value}>
                {pri.label}
              </option>
            ))}
          </select>
        </div>

        {/* Message Field */}
        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-1">
            Message *
          </label>
          <textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleInputChange}
            rows={6}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            aria-required="true"
            disabled={status === 'submitting'}
            maxLength={1000}
          />
          <div className="flex justify-between items-center mt-1">
            {error && error.includes('Message') && (
              <p className="text-red-600 text-sm">{error}</p>
            )}
            <span className={`text-sm ${charCount > 900 ? 'text-red-600' : 'text-gray-500'} ${!error || !error.includes('Message') ? 'ml-auto' : ''}`}>
              {charCount}/1000
            </span>
          </div>
        </div>

        {/* Submit Button */}
        <div>
          <button
            type="submit"
            disabled={status === 'submitting'}
            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {status === 'submitting' ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Submitting...
              </>
            ) : (
              'Submit Request'
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && !error.includes('Name') && !error.includes('email') && !error.includes('Subject') && !error.includes('Message') && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}
      </form>
    </div>
  )
}

export default SupportForm
