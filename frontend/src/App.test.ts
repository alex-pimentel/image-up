import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import App from './App.vue'
import { api } from './services/api'
import type { Health, Limits } from './types'

const limits: Limits = {
  max_upload_mb: 8,
  max_input_px: 1000,
  allowed_extensions: ['png', 'jpg'],
  output_quality: 95,
  output_format: 'webp',
}

const health: Health = {
  status: 'ok',
  version: '0.1.0',
  ml_available: false,
  backend: 'fallback',
  model_name: null,
}

const makeWrapper = () =>
  mount(App, {
    global: {
      stubs: {
        SelectButton: { template: '<div class="selectbutton-stub" />' },
      },
    },
  })

describe('App', () => {
  beforeEach(() => {
    vi.spyOn(api, 'getHealth').mockResolvedValue(health)
    vi.spyOn(api, 'getConfig').mockResolvedValue(limits)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads health and config on mount and renders the backend badge', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.text()).toContain('backend: fallback')
    expect(wrapper.text()).toContain('Enhance & upscale your images with AI')
  })

  it('surfaces an error banner when the API is unreachable', async () => {
    vi.spyOn(api, 'getHealth').mockRejectedValue(new Error('boom'))
    vi.spyOn(api, 'getConfig').mockRejectedValue(new Error('boom'))

    const wrapper = makeWrapper()
    await flushPromises()

    expect(wrapper.text()).toContain('Cannot reach backend API')
  })

  it('submits a selected file and shows the comparer once done', async () => {
    const enhance = vi
      .spyOn(api, 'enhance')
      .mockResolvedValue({ task_id: 'task-1', status: 'pending' })
    vi.spyOn(api, 'asset').mockImplementation((u) => u)

    let pollCb: ((r: unknown) => void) | null = null
    vi.spyOn(api, 'pollStatus').mockImplementation((_id, cb) => {
      pollCb = cb as typeof pollCb
      return () => {}
    })

    const wrapper = makeWrapper()
    await flushPromises()

    const zone = wrapper.findComponent({ name: 'UploadZone' })
    zone.vm.$emit('select', new File(['x'], 'photo.png', { type: 'image/png' }), 'blob:preview')
    await flushPromises()

    expect(enhance).toHaveBeenCalled()

    pollCb!({
      task_id: 'task-1',
      status: 'done',
      original_filename: 'photo.png',
      original_url: '/api/results/orig.png',
      result_url: '/api/results/out.png',
      elapsed_sec: 2,
      detail: null,
      backend: 'fallback',
    })
    await flushPromises()

    expect(wrapper.findComponent({ name: 'ImageComparer' }).exists()).toBe(true)
    expect(wrapper.text()).toContain('Download enhanced image')
  })

  it('reports an enhance failure to the user', async () => {
    vi.spyOn(api, 'enhance').mockRejectedValue(new Error('File too large'))
    vi.spyOn(api, 'pollStatus').mockReturnValue(() => {})

    const wrapper = makeWrapper()
    await flushPromises()

    const zone = wrapper.findComponent({ name: 'UploadZone' })
    zone.vm.$emit('select', new File(['x'], 'photo.png', { type: 'image/png' }), 'blob:preview')
    await flushPromises()

    expect(wrapper.text()).toContain('File too large')
  })

  it('resets back to the upload zone', async () => {
    vi.spyOn(api, 'enhance').mockResolvedValue({ task_id: 'task-1', status: 'pending' })
    vi.spyOn(api, 'asset').mockImplementation((u) => u)
    vi.spyOn(api, 'pollStatus').mockImplementation((_id, cb) => {
      ;(cb as (r: unknown) => void)({
        task_id: 'task-1',
        status: 'done',
        original_filename: 'photo.png',
        original_url: '/o.png',
        result_url: '/r.png',
        elapsed_sec: 1,
        detail: null,
        backend: 'fallback',
      })
      return () => {}
    })

    const wrapper = makeWrapper()
    await flushPromises()
    wrapper
      .findComponent({ name: 'UploadZone' })
      .vm.$emit('select', new File(['x'], 'p.png', { type: 'image/png' }), 'blob:p')
    await flushPromises()

    const resetBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Enhance another image'))
    expect(resetBtn).toBeTruthy()
    await resetBtn!.trigger('click')

    expect(wrapper.findComponent({ name: 'UploadZone' }).exists()).toBe(true)
  })
})
