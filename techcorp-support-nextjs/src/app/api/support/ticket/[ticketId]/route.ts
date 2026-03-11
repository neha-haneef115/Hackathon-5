import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { ticketId: string } }
) {
  try {
    const { ticketId } = params
    
    // Forward request to FastAPI backend
    const response = await fetch(`http://localhost:8000/support/ticket/${ticketId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      const errorData = await response.text()
      console.error('Backend error:', errorData)
      return NextResponse.json(
        { error: 'Failed to retrieve ticket information' },
        { status: response.status }
      )
    }
    
    const data = await response.json()
    return NextResponse.json(data, { status: 200 })
    
  } catch (error) {
    console.error('API route error:', error)
    return NextResponse.json(
      { error: 'Failed to retrieve ticket information' },
      { status: 500 }
    )
  }
}
