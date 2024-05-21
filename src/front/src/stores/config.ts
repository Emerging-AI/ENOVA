interface InstanceType {
  instance_id: 'string'
  instance_name: 'string'
  instance_spec: {
    cpu: {
      brand_name: string
      core_amount: number
    }
    gpu: {
      product: string
      video_memory: string
      card_amount: number
    }
    memory: string
  }
  startup_args: {
    exported_job: string
    dtype: string
    load_format: string
    max_num_batched_tokens: number
    max_num_seqs: number
    max_paddings: number
    max_seq_len: number
    model: string
    tokenizer: string
    pipeline_parallel_size: number
    tensor_parallel_size: number
    quantization: null
  }
  enode_id: string
  deploy_status: string
  create_time: string
}

interface ExperimentType {
  test_id: string
  instance_id: string
  test_spec: {
    data_set: string
    duration: 0
    duration_unit: string
    distribution: string
    tps_mean: 0
    tps_std?: string
  }
  param_spec: {
    max_tokens: number
    temperature: number
    top_p: number
    others: string
  }
  test_status: string
  prompt_tps: number
  generation_tps: number
  result: {
    total: number
    success: number
    elasped_avg: number
  }
  create_time: string
}

export type { InstanceType, ExperimentType }
