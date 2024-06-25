export default {
  common: {
    lang: {
      zh: '简体中文',
      en: 'English'
    },
    title: {
      operation: '操作',
      createTime: '创建时间',
      creator: '创建人',
      startTime: '开始时间',
      endTime: '结束时间',
      to: '至',
      baseInfo: '基本信息',
      metrics: '指标',
      testIndicator: '测试指标',
      data: '数据',
      parameters: '参数',
      dataset: '数据集',
      noContrast: '不对比',
      customContrast: '指定对比周期',
      noRefresh: '关闭',
      customRefresh: '指定刷新周期',
      time: '时间',
      failure: '失败',
      causes: '原因',
      unknown: '未知'
    },
    action: {
      delete: '删除',
      operationLog: '操作日志',
      cancel: '取消',
      refresh: '刷新'
    },
    inst: {
      deleteTips: '确认删除？'
    },
    time: {
      lastHour: '前1时',
      lastDay: '前1日',
      lastWeek: '前1周',
      lastMonth: '前1月',
      hour: '时',
      minute: '分',
      second: '秒',
      day: '日',
      week: '周'
    }
  },
  menu: {
    service: 'LLM部署实例',
    record: '测试记录'
  },
  instance: {
    title: {
      llmInstance: 'LLM部署实例',
      instanceName: '实例名称',
      deployStatus: '部署状态',
      deploying: '部署中',
      deploySuccess: '部署成功',
      deployFail: '部署失败',
      finished: '执行结束',
      instanceDetail: 'LLM部署实例详情',
      testConfig: '测试配置',
      startupOptions: '启动参数',
      instanceSpec: '实例规格',
      instanceImage: '实例镜像',
      area: '地区',
      memory: '内存',
      systemDisk: '系统盘',
      dataDisk: '数据盘',
      imageSource: '镜像来源',
      image: '镜像',
      injectTime: '流量注入时长',
      distribution: '流量分布',
      poisson: '泊松分布',
      traffic: '正态分布',
      otherParams: '其他参数',
      sysDataset: '官方数据集',
      userDataset: '自定义数据集',
      configSuggest: '配置建议',
      currentVal: '当前值',
      suggestVal: '建议值'
    },
    action: {
      inject: '注入测试',
      startTest: '开始测试'
    },
    inst: {
      searchPlaceholder: '实例名称、部署状态',
      datasetPlaceholder: '请选择数据集',
      paramsPlaceholder: '请选择参数值',
      chartSearch: '指标名称、指标类型',
      durationTip: '持续{0}'
    }
  },
  experiment: {
    title: {
      testRecord: '测试记录',
      testResult: '测试结果',
      testLog: '测试日志',
      testTime: '测试时间',
      testId: '测试ID',
      testInstance: '测试实例',
      testDataset: '测试数据集',
      testStatus: '测试状态',
      prompt: '平均每秒 Prompt 吞吐量',
      generation: '平均每秒 Generation 吞吐量',
      testUser: '测试人',
      testing: '测试中',
      testSuccess: '测试成功',
      testFail: '测试失败',
      testInit: '未测试',
      testUnknown: '未测试',
      finished: '测试结束',
      testResultOverview: '测试结果总览',
      testConfig: '测试配置',
      requestNum: '发送总请求数',
      requestSuccessNum: '请求执行成功数',
      requestSuccessRate: '请求执行成功率',
      avgTime: '请求平均执行时间'
    },
    action: {},
    inst: {
      searchPlaceholder: '测试实例、测试数据集',
      successTip: '注入测试成功！'
    }
  },
  datepicker: {
    placeholder: '选择日期时间',
    to: '至',
    startDate: '开始日期',
    endDate: '结束日期',
    today: '今天',
    lastWeek: '最近1周',
    lastMonth: '最近30天',
    lastThreeMonths: '最近3个月',
    lastTwelveHours: '最近12小时',
    lastOneHour: '最近1小时',
    lastThreeHours: '最近3小时',
    lastTwentyFourHours: '最近24小时',
    lastTwoDays: '最近2天',
    lastSevenDays: '最近7天',
    day: '天',
    hour: '小时',
    minute: '分钟'
  },
  chart: {
    title: {
      requestNum: '每秒收到的请求数',
      requestExecuteNum: '每秒返回的请求数',
      requestSuccessNum: '每秒成功执行的请求数',
      requestSuccessRate: '请求执行的成功率',
      activeRequestNum: '正在处理中的请求数量',
      requestDuration: '每秒平均请求执行时间',
      responseSize: '每秒发送的请求大小',
      requestSize: '每秒处理的请求大小',
      promptThroughput: 'Prompt输入速率',
      generationThroughput: '生成速率',
      runningRequests: '正在运行的请求数',
      pendingRequests: '等待中的请求数',
      gpuKv: 'KV cache使用率',
      gpuRate: 'GPU利用率',
      memRate: '内存带宽利用率',
      fbNum: '显存已使用数',
      smClock: 'SM时钟频率',
      memClock: '内存时钟频率',
      memTemp: '内存温度',
      gpuTemp: 'GPU温度',
      power: '功率',
      grEnginActive: '图形引擎活动',
      tensor: 'Tensor核心使用率',
      memCopyUtil: '内存带宽利用率',
      pcie: 'PCIE总线速率',
      nvLink: 'NVLink速率',
      noData: '目前尚无相关数据'
    }
  }
}
