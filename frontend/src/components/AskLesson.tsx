import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { assistantApi } from '../api/endpoints'
import { ApiError } from '../api/client'

interface Exchange {
  question: string
  answer?: string // undefined while the assistant is thinking
}

/** Lesson-scoped Q&A: ask about the lesson you're reading, answered by the
 *  learning assistant grounded in this course's content. Conversation is
 *  page-local — it's a study aid, not a saved chat. */
export function AskLesson({ courseId, assetId }: { courseId: string; assetId: string }) {
  const [question, setQuestion] = useState('')
  const [exchanges, setExchanges] = useState<Exchange[]>([])
  const [error, setError] = useState<string | null>(null)

  const askMutation = useMutation({
    mutationFn: (q: string) =>
      assistantApi.ask({ course_id: courseId, asset_id: assetId, question: q }),
    onSuccess: (res, q) => {
      setError(null)
      setExchanges((prev) =>
        prev.map((e) => (e.question === q && e.answer === undefined ? { ...e, answer: res.answer } : e))
      )
    },
    onError: (err, q) => {
      setExchanges((prev) => prev.filter((e) => !(e.question === q && e.answer === undefined)))
      setError(err instanceof ApiError ? err.message : 'The assistant could not answer.')
    },
  })

  function submit() {
    const q = question.trim()
    if (!q || askMutation.isPending) return
    setExchanges((prev) => [...prev, { question: q }])
    setQuestion('')
    askMutation.mutate(q)
  }

  return (
    <div className="border-t border-line bg-paper/50 px-5 py-4">
      <p className="eyebrow mb-2">Ask about this lesson</p>

      {exchanges.length > 0 && (
        <div className="mb-3 flex flex-col gap-3">
          {exchanges.map((e, i) => (
            <div key={i} className="flex flex-col gap-2">
              <p className="max-w-[62ch] self-end rounded-[10px] bg-primary/8 px-3 py-2 text-sm text-ink">
                {e.question}
              </p>
              {e.answer === undefined ? (
                <p className="text-sm text-faint">Thinking…</p>
              ) : (
                <p className="max-w-[62ch] whitespace-pre-wrap rounded-[10px] border border-line bg-surface px-3 py-2 text-sm leading-relaxed text-ink/85">
                  {e.answer}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <input
          className="field-input"
          placeholder="Didn't get something? Ask here — e.g. “why does FastAPI appear twice?”"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') submit()
          }}
        />
        <button
          type="button"
          className="btn btn-primary btn-sm shrink-0"
          disabled={!question.trim() || askMutation.isPending}
          onClick={submit}
        >
          Ask
        </button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
