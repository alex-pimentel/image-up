import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UploadZone from './UploadZone.vue'
import type { Limits } from '../types'

const limits: Limits = {
  max_upload_mb: 8,
  max_input_px: 1000,
  allowed_extensions: ['png', 'jpg'],
  output_quality: 95,
  output_format: 'webp',
}

describe('UploadZone', () => {
  it('renders the allowed extensions from limits', () => {
    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })

    expect(wrapper.text()).toContain('Drag & drop an image here')
    expect(wrapper.text()).toContain('png, jpg')
  })

  it('shows the propagated error message', () => {
    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: 'Cannot reach backend API' },
    })

    expect(wrapper.text()).toContain('Cannot reach backend API')
  })

  it('rejects an unsupported extension without emitting', async () => {
    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })

    const onSelect = vi.spyOn(wrapper.vm, '$emit')
    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'photo.gif', { type: 'image/gif' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')

    expect(onSelect).not.toHaveBeenCalledWith('select', expect.anything(), expect.anything())
    expect(wrapper.text()).toContain('Unsupported extension')
  })

  it('rejects a file over the size limit', async () => {
    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })

    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'photo.png', { type: 'image/png' })
    Object.defineProperty(file, 'size', { value: 9 * 1024 * 1024 })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')

    expect(wrapper.text()).toContain('File too large')
  })

  it('emits select for a valid image within the pixel limit', async () => {
    const createObjectURL = vi.fn(() => 'blob:preview')
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL: vi.fn() })

    // Minimal 1x1 image; Image.onload fires synchronously via the mock below.
    const RealImage = globalThis.Image
    class FakeImage {
      width = 1
      height = 1
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      set src(_v: string) {
        this.onload?.()
      }
    }
    vi.stubGlobal('Image', FakeImage as unknown as typeof RealImage)

    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })

    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'photo.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.emitted('select')).toBeTruthy()
    expect(wrapper.emitted('select')![0][0]).toBe(file)
    expect(createObjectURL).toHaveBeenCalledWith(file)

    vi.unstubAllGlobals()
  })

  it('rejects an image whose longest side exceeds the pixel limit', async () => {
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:big'), revokeObjectURL: vi.fn() })
    const RealImage = globalThis.Image
    class FakeImage {
      width = 2000
      height = 1500
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      set src(_v: string) {
        this.onload?.()
      }
    }
    vi.stubGlobal('Image', FakeImage as unknown as typeof RealImage)

    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })
    const input = wrapper.find('input[type="file"]')
    const file = new File(['x'], 'photo.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()

    expect(wrapper.text()).toContain('too large')
    expect(wrapper.emitted('select')).toBeFalsy()

    vi.unstubAllGlobals()
  })

  it('falls back to defaults when limits are null', () => {
    const wrapper = mount(UploadZone, {
      props: { limits: null, busy: false, error: null },
    })

    expect(wrapper.text()).toContain('Allowed:')
  })

  it('handles a drag & drop of files', async () => {
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:drag'), revokeObjectURL: vi.fn() })
    const RealImage = globalThis.Image
    class FakeImage {
      width = 10
      height = 10
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      set src(_v: string) {
        this.onload?.()
      }
    }
    vi.stubGlobal('Image', FakeImage as unknown as typeof RealImage)

    const wrapper = mount(UploadZone, {
      props: { limits, busy: false, error: null },
    })
    const file = new File(['x'], 'photo.png', { type: 'image/png' })
    await wrapper.find('.upload-zone').trigger('drop', { dataTransfer: { files: [file] } })
    await flushPromises()

    expect(wrapper.emitted('select')).toBeTruthy()

    vi.unstubAllGlobals()
  })
})
