import type { RecommendedJob, UserProfile } from '../types';

export async function getJobRecommendations(profile: UserProfile): Promise<RecommendedJob[]> {
  // Show the loading state of the local example flow.
  await new Promise<void>((resolve) => window.setTimeout(resolve, 850));

  const skills = profile.skills.slice(0, 3).join('、');
  const traits = profile.personality.join('、');

  return [
    {
      id: 'product-operations',
      title: '产品运营',
      reason: '可查看与产品落地、用户增长和跨团队协作相关的 JD。',
      focus: ['目标拆解', '数据分析', '跨团队协作'],
      gaps: ['补充数据分析案例', '展示完整的项目结果与指标'],
    },
    {
      id: 'user-research',
      title: '用户研究助理',
      reason: skills
        ? `可对照 JD 核实你填写的「${skills}」是否能支持研究工作。`
        : '可关注以访谈、问卷和用户反馈分析为主的 JD。',
      focus: ['信息归纳', '跨角色沟通', '研究方法'],
      gaps: ['补充访谈或问卷实践', '熟悉基础研究方法'],
    },
    {
      id: 'project-coordinator',
      title: '项目协调专员',
      reason: traits
        ? `可找出能体现「${traits}」的真实例子，再与 JD 中的项目推进职责对照。`
        : '可查看项目排期、任务跟进和协作沟通相关的 JD。',
      focus: ['项目排期', '任务跟进', '沟通协作'],
      gaps: ['补充项目排期经验', '突出风险跟进与复盘成果'],
    },
  ];
}
