import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Forward the request to the FastAPI backend
    const response = await fetch('http://localhost:8000/support/submit', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })
    
    if (!response.ok) {
      const errorData = await response.text()
      console.error('Backend error:', errorData)
      return NextResponse.json(
        { error: 'Failed to submit request. Please try again.' },
        { status: 500 }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('API route error:', error)
    return NextResponse.json(
      { error: 'Failed to submit request. Please try again.' },
      { status: 500 }
    )
  }
}
