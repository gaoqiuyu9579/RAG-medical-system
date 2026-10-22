import request from "./request"

export function getKnowledgeStatus() {
    return request.get('/rag/status')
}



export function chat(question){
    return request.post("/rag/chat", {question})
}



export function uploadKnowledge(text){
    return request.post("/rag/upload", {text})
}



export function uploadFile(file){
    const formData = new FormData()
    formData.append('file', file)
    return request.post("/rag/upload-file", formData)
}
