import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from './api'

const jsonResponse = (body: unknown, ok = true, status = 200) =>
  ({
    ok,
    status,
    statusText: ok ? 'OK' : 'Bad Request',
    json: async () => body,
  }) as Response

describe('api service', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('getHealth fetches /api/health', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        status: 'ok',
        version: '0.1.0',
        ml_available: false,
        backend: 'fallback',
        model_name: null,
      }),
    )

    const health = await api.getHealth()

    expect(health.backend).toBe('fallback')
    expect(mockFetch).toHaveBeenCalledWith('/api/health')
  })

  it('getConfig fetches /api/config', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce(
      jsonResponse({
        max_upload_mb: 8,
        max_input_px: 1000,
        allowed_extensions: ['png'],
        output_quality: 95,
        output_format: 'webp',
      }),
    )

    const limits = await api.getConfig()

    expect(limits.max_upload_mb).toBe(8)
    expect(mockFetch).toHaveBeenCalledWith('/api/config')
  })

  it('enhance posts a multipart form', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce(jsonResponse({ task_id: 'abc', status: 'pending' }))

    const file = new File(['x'], 'photo.png', { type: 'image/png' })
    const res = await api.enhance(file, 4)

    expect(res.task_id).toBe('abc')
    const [url, init] = mockFetch.mock.calls[0]
    expect(url).toBe('/api/enhance?scale=4')
    expect((init as RequestInit).method).toBe('POST')
    expect((init as RequestInit).body).toBeInstanceOf(FormData)
  })

  it('throws the server detail on a non-ok response', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce(jsonResponse({ detail: 'File too large' }, false, 413))

    await expect(api.getConfig()).rejects.toThrow('File too large')
  })

  it('falls back to statusText when the error body is not JSON', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Server Error',
      json: async () => {
        throw new Error('not json')
      },
    } as unknown as Response)

    await expect(api.getConfig()).rejects.toThrow('Server Error')
  })

  it('pollStatus stops once the task is done', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue(
      jsonResponse({
        task_id: 'abc',
        status: 'done',
        original_filename: null,
        original_url: '/api/results/a.png',
        result_url: '/api/results/b.png',
        elapsed_sec: 1.2,
        detail: null,
        backend: 'fallback',
      }),
    )

    const onUpdate = vi.fn()
    api.pollStatus('abc', onUpdate, 1000)
    await vi.advanceTimersByTimeAsync(1000)

    expect(onUpdate).toHaveBeenCalledTimes(1)
    expect(onUpdate.mock.calls[0][0].status).toBe('done')
  })

  it('pollStatus reports an error when the fetch fails', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockRejectedValue(new Error('network down'))

    const onUpdate = vi.fn()
    api.pollStatus('abc', onUpdate, 1000)
    await vi.advanceTimersByTimeAsync(1000)

    expect(onUpdate).toHaveBeenCalledTimes(1)
    expect(onUpdate.mock.calls[0][0].status).toBe('error')
  })

  it('pollStatus can be cancelled before it fires', async () => {
    const mockFetch = fetch as unknown as ReturnType<typeof vi.fn>
    mockFetch.mockResolvedValue(jsonResponse({ task_id: 'abc', status: 'processing' }))

    const onUpdate = vi.fn()
    const stop = api.pollStatus('abc', onUpdate, 1000)
    stop()
    await vi.advanceTimersByTimeAsync(5000)

    expect(onUpdate).not.toHaveBeenCalled()
  })

  it('asset prefixes the API base and passes null through', () => {
    expect(api.asset('/api/results/x.png')).toBe('/api/results/x.png')
    expect(api.asset(null)).toBeNull()
  })
})
