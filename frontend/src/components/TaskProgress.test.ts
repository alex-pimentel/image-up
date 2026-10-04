import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskProgress from './TaskProgress.vue'
import type { Limits } from '../types'

const limits: Limits = {
  max_upload_mb: 8,
  max_input_px: 1000,
  allowed_extensions: ['png', 'jpg'],
  output_quality: 95,
  output_format: 'webp',
}

describe('TaskProgress', () => {
  it('shows elapsed time and backend when provided', () => {
    const wrapper = mount(TaskProgress, {
      props: {
        progressLabel: 'Enhancing image…',
        elapsed: 1.234,
        backend: 'fallback',
        limits: null,
        running: true,
      },
    })

    expect(wrapper.text()).toContain('Enhancing image…')
    expect(wrapper.text()).toContain('Elapsed: 1.23s')
    expect(wrapper.text()).toContain('fallback')
  })

  it('shows the input size restriction reminder when limits exist', () => {
    const wrapper = mount(TaskProgress, {
      props: {
        progressLabel: 'Done',
        elapsed: null,
        backend: null,
        limits,
        running: false,
      },
    })

    expect(wrapper.text()).toContain('1000px')
    expect(wrapper.text()).not.toContain('Elapsed')
  })
})
