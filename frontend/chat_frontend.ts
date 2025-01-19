//  Date: 18.01.2025
// 
//  Author: Amanda Uccello
//  Class: ICS4UR-1
//  School: Port Credit Secondary School
//  Teacher: Mrs. Kim
//  Description: 
//      Handles the code required for the frontend of the Amanda AI chat


import { marked } from 'https://cdnjs.cloudflare.com/ajax/libs/marked/15.0.0/lib/marked.esm.js'
const convElement = document.getElementById('conversation')
const promptInput = document.getElementById('prompt-input') as HTMLInputElement
const spinner = document.getElementById('spinner')

// output the response from the server
async function onFetchResponse(response: Response): Promise<void> {
  let text = ''
  let decoder = new TextDecoder()
  if (response.ok) {
    const reader = response.body.getReader()
    while (true) {
      const {done, value} = await reader.read()
      if (done) {
        break
      }
      text += decoder.decode(value)
      addMessages(text)
      spinner.classList.remove('active')
    }
    addMessages(text)
    promptInput.disabled = false
    promptInput.focus()
  } else {
    const text = await response.text()
    console.error(`Unexpected response: ${response.status}`, {response, text})
    throw new Error(`Unexpected response: ${response.status}`)
  }
}

// The message format that the server sends
interface Message {
  role: string
  content: string
  timestamp: string
}

// Add messages to the conversation 
function addMessages(responseText: string) {
  const lines = responseText.split('\n')
  const messages: Message[] = lines.filter(line => line.length > 1).map(j => JSON.parse(j))
  for (const message of messages) {
    
    const {timestamp, role, content} = message
    const id = `msg-${timestamp}`
    let msgDiv = document.getElementById(id)
    if (!msgDiv) {
      msgDiv = document.createElement('div')
      msgDiv.id = id
      msgDiv.title = `${role} at ${timestamp}`
      msgDiv.classList.add('border-top', 'pt-2', role)
      convElement.appendChild(msgDiv)
    }
    msgDiv.innerHTML = marked.parse(content)
  }
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
}

function onError(error: any) {
  console.error(error)
  document.getElementById('error').classList.remove('d-none')
  document.getElementById('spinner').classList.remove('active')
  spinner.classList.remove('active')
}

async function onSubmit(e: SubmitEvent): Promise<void> {
  e.preventDefault()
  spinner.classList.add('active')
  const messageDiv = document.getElementById('message')!
  messageDiv.innerHTML = `<div class="hidden"></div>`

  const fileInput = document.getElementById('fileInput') as HTMLInputElement
  fileInput.value = ''

  const body = new FormData(e.target as HTMLFormElement)

  promptInput.value = ''
  promptInput.disabled = true

  const response = await fetch('/chat/', {method: 'POST', body})
  await onFetchResponse(response)
}

async function onFileUpload(e: SubmitEvent): Promise<void> {
  e.preventDefault()
  spinner.classList.add('active')

  const fileInput = document.getElementById('fileInput') as HTMLInputElement
  console.log('File:', fileInput);

  const form = e.target as HTMLFormElement;
  console.log('Form:', form);

  const body = new FormData(form)
  console.log('Form data:', body);

  const response = await fetch('/upload/', { method: 'POST', body })
  const result = await response.json()
  const messageDiv = document.getElementById('message')!
  if (response.ok) {
    messageDiv.innerHTML = `<div class="alert alert-success">${result.message}</div>`
  } else {
    messageDiv.innerHTML = `<div class="alert alert-danger">${result.message}</div>`
  }
  spinner.classList.remove('active')
}

// call onSubmit when the form is submitted or when the user presses enter
document.getElementById('chatInput').addEventListener('submit', (e) => onSubmit(e).catch(onError))


document.getElementById('uploadForm').addEventListener('submit', (e) => { onFileUpload(e).catch(onError) })

document.getElementById('showFormButton')!.addEventListener('click', () => {
  const uploadForm = document.getElementById('uploadForm')!
  uploadForm.style.display = 'block'
  const showFormButton = document.getElementById('showFormButton')!
  showFormButton.style.display = 'none'
})

document.getElementById('hideFormButton')!.addEventListener('click', () => {
  const uploadForm = document.getElementById('uploadForm')!
  uploadForm.style.display = 'none'
  const showFormButton = document.getElementById('showFormButton')!
  showFormButton.style.display = 'block'
})

// load messages on page load
fetch('/chat/').then(onFetchResponse).catch(onError)
