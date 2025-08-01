# python: 2.7
# encoding: utf-8
# 导入numpy模块并命名为np
import numpy as np  # 导入NumPy库用于高效数值计算
import sys  # 导入系统相关模块，用于获取Python版本、操作路径等

class RBM:
    """Restricted Boltzmann Machine.（受限玻尔兹曼机）"""

    def __init__(self, n_hidden=2, n_observe=784):
        """
        初始化受限玻尔兹曼机（RBM）模型参数

        Args:
            n_hidden (int): 隐藏层单元数量（默认 2）
            n_observe (int): 可见层单元数量（默认 784，如 MNIST 图像 28x28）

        Raises:
            ValueError: 若输入的参数非正整数则抛出异常
        """
        # 参数验证：确保隐藏层和可见层单元数量为正整数
        if not (isinstance(n_hidden, int) and n_hidden > 0):            # 如果任一条件不满足，抛出 ValueError 异常，提示用户 n_hidden 必须为正整数
            raise ValueError("隐藏层单元数量 n_hidden 必须为正整数")      # 如果任一条件不满足，抛出 ValueError 异常，提示用户 n_hidden 必须为正整数
        if not (isinstance(n_observe, int) and n_observe > 0):          # 若条件不满足，后续逻辑可能产生异常或无意义结果
            raise ValueError("可见层单元数量 n_observe 必须为正整数")
        # 初始化模型参数
        self.n_hidden = n_hidden    # 设置隐藏层的神经元数量
        self.n_observe = n_observe  # 设置可见层的神经元数量
        
        # 权重矩阵 (可见层到隐藏层)
        # 使用标准正态分布，标准差为0.1，确保权重初始值较小且分布合理
        self.W = np.random.normal(
        loc = 0.0,                # 均值
        scale = 0.1,              # 标准差（常见初始化方法）
        size = (n_observe, n_hidden)) # 定义了一个元组 size，其中包含两个元素：n_observe 和 n_hidden
        
        # 初始化权重矩阵W，使用正态分布随机初始化
        # 可见层偏置（1 x n_observe）
        self.Wv = np.zeros((1, n_observe))
        
        # 隐藏层偏置（1 x n_hidden）
        self.Wh = np.zeros((1, n_hidden))
        
        # 可选：使用 Xavier/Glorot 初始化替代
        # self.W = np.random.randn(n_observe, n_hidden) * np.sqrt(1.0 / n_observe)
        # self.Wv = np.zeros((1, n_observe))
        # self.Wh = np.zeros((1, n_hidden))

        # 确保隐藏层和可见层的单元数量为正整数
        # 神经网络模型的一部分，用于初始化隐藏层和可见层的权重和偏置
        # 参数初始化
        self.n_hidden = n_hidden     # 隐藏层神经元个数
        self.n_observe = n_observe   # 可见层神经元个数

        # 初始化权重和偏置
        # 使用 Xavier 初始化方法：标准差 = sqrt(2 / (输入维度 + 输出维度))
        init_std = np.sqrt(2.0 / (self.n_observe + self.n_hidden))  # Xavier初始化标准差

        self.W = np.random.normal(
            0, init_std, size=(self.n_observe, self.n_hidden)
        )  # 初始化权重矩阵（可见层 -> 隐藏层）

        # 可选替代方案：使用更小的固定标准差进行初始化。
        # self.W = np.random.normal(0, 0.01, size=(n_observe, n_hidden))
        # 最终使用的偏置向量（与上方Wv/Wh重复，统一使用b_h和b_v）
        self.b_h = np.zeros(n_hidden)   # 初始化隐藏层偏置向量

        self.b_v = np.zeros(n_observe)  # 初始化可见层偏置向量
        # pass
    
    def _sigmoid(self, x):
        """Sigmoid激活函数，用于将输入映射到概率空间
        将任意实数映射到(0,1)区间，适合表示神经元的激活概率
        """
        return 1.0 / (1 + np.exp(-x))  # 计算Sigmoid函数的值，公式为1 / (1 + e^(-x))，将输入x映射到(0,1)区间

    def _sample_binary(self, probs):
        """伯努利采样生成二进制值
    
    Args:
        probs (ndarray): 概率值数组，范围[0,1]
        
    Returns:
        ndarray: 采样结果（0或1）
        
    Raises:
        ValueError: 概率值超出[0,1]范围时抛出
    """
        # 确保probs的取值在[0, 1]范围内
        if np.any(probs < 0) or np.any(probs > 1):
            raise ValueError("概率值probs应在0和1之间。")
            
        # 通过np.random.binomial进行伯努利采样，n=1表示单次试验，probs表示成功的概率
        return np.random.binomial(1, probs)  # 生成伯努利随机变量，以概率probs返回1，否则返回0
    
    def train(self, data):
        """
        使用 k=1 的 Contrastive Divergence (CD-1) 算法训练 RBM

        CD-1 算法流程：
        1. 从训练数据初始化可见层 v₀
        2. 正向传播：v₀ → h₀（计算隐藏层激活概率并采样）
        3. 反向传播：h₀ → v₁（重构可见层）
        4. 再次正向传播：v₁ → h₁（计算重构后的隐藏层概率）
        5. 基于正负相位的梯度更新参数

        参数更新公式（最大化对数似然）：
        ΔW = η · (⟨v₀h₀⟩ - ⟨v₁h₁⟩)
        Δb_v = η · (v₀ - v₁)
        Δb_h = η · (h₀ - h₁)
        
        注：⟨v₀h₀⟩ 表示 v₀ 和 h₀ 的外积期望，即数据驱动的正相位
            ⟨v₁h₁⟩ 表示 v₁ 和 h₁ 的外积期望，即模型生成的负相位
        """
    
        # 将数据展平为二维数组 [n_samples, n_observe]，确保输入数据符合模型要求
        data_flat = data.reshape(data.shape[0], -1)  
        n_samples = data_flat.shape[0]  # 样本数量

        # 定义训练参数
        learning_rate = 0.1  # 学习率，控制参数更新的步长
        
        epochs = 10  # 训练轮数，整个数据集将被遍历10次
        
        batch_size = 100  # 批处理大小，每次更新参数使用的样本数量

        # 开始训练轮数
        for epoch in range(epochs):
            # 打乱数据顺序，提高训练稳定性和泛化能力，避免模型学习到特定的样本顺序
            
            np.random.shuffle(data_flat) 
            
            # 使用小批量梯度下降法
            for i in range(0, n_samples, batch_size): 
                # 获取当前批次的数据
                batch = data_flat[i:i + batch_size]  # 使用切片操作从ata_flat中提取从第i行到第i+batch_size行的子数组
                
                # 将批次数据转换为 float64 类型，确保数值计算的精度
                v0 = batch.astype(np.float64)  # 确保数据类型正确

                # 正相传播：从v0计算隐藏层激活概率
                # 计算可见层对隐藏层的输入：输入层向量v0与权重矩阵self.W的点积，再加上隐藏层偏置self.b_h
                # 条件概率：P(h_j=1|v) = σ(b_j + Σ_i v_i·W_ij)
                h0_prob = self._sigmoid(np.dot(v0, self.W) + self.b_h) 
                
                # 对隐藏层激活概率进行二值采样，得到隐藏层的状态
                h0_sample = self._sample_binary(h0_prob) 
                # 这段代码的作用是借助 self._sample_binary 方法，对 h0_prob 进行二值采样，进而得到 h0_sample。在深度学习领域，当处理二值变量或者进行二值掩码操作时，常常会用到这样的采样。

                # 负相传播：从隐藏层重构可见层，再计算隐藏层概率
                # 计算隐藏层对可见层的重构输入：隐藏层状态h0_sample与权重矩阵转置self.W.T的点积，再加上可见层偏置self.b_v
                # 条件概率：P(v_i=1|h) = σ(a_i + Σ_j h_j·W_ij)
                v1_prob = self._sigmoid(np.dot(h0_sample, self.W.T) + self.b_v)  # 将上述结果传入 Sigmoid 激活函数进行非线性变换，得到最终的概率值 v1_prob
                
                # 对可见层重构概率进行二值采样，得到重构的可见层状态
                v1_sample = self._sample_binary(v1_prob)  # 对可见层进行二值采样
                
                # 基于重构的可见层状态，再次计算隐藏层激活概率
                h1_prob = self._sigmoid(np.dot(v1_sample, self.W) + self.b_h)       # 计算隐藏单元被激活的概率

                # 计算梯度      
                # 权重矩阵梯度：数据驱动的正相位与模型生成的负相位之差
                dW = np.dot(v0.T, h0_sample) - np.dot(v1_sample.T, h1_prob)          # 计算权重矩阵的梯度
                
                # 可见层偏置梯度：原始数据与重构数据之差
                db_v = np.sum(v0 - v1_sample, axis=0)                                # 计算可见层偏置的梯度
                
                # 隐藏层偏置梯度：原始数据生成的隐藏层状态与重构数据生成的隐藏层状态之差
                db_h = np.sum(h0_sample - h1_prob, axis=0)                           # 计算隐藏层偏置的梯度

                # 更新参数
                # 按批次大小归一化梯度，并乘以学习率更新权重矩阵
                self.W += learning_rate * dW / batch_size                            # 更新权重矩阵
                
                # 按批次大小归一化梯度，并乘以学习率更新可见层偏置
                self.b_v += learning_rate * db_v / batch_size                        # 更新可见层偏置
                
                # 按批次大小归一化梯度，并乘以学习率更新隐藏层偏置
                self.b_h += learning_rate * db_h / batch_size                        # 更新隐藏层偏置

    def sample(self):
        """从训练好的模型中采样生成新数据（Gibbs采样）
        通过多次Gibbs采样迭代，模型能够从学习到的数据分布中生成新样本
        """
        # 初始化可见层：使用伯努利分布随机生成二值向量（每个像素有50%概率为1）
        # n_observe是可见层神经元数量（28x28=784）
        v = np.random.binomial(1, 0.5, self.n_observe)

        # 进行1000次 Gibbs采样迭代，以逐步趋近真实数据分布，使生成的样本更接近训练数据的分布
        # 每次迭代包括：v -> h -> v 的完整过程
        for _ in range(1000):
            # 基于当前的可见层v，计算隐藏层神经元被激活的概率（前向传播）
            h_prob = self._sigmoid(np.dot(v, self.W) + self.b_h)

            # 根据激活概率采样得到隐藏层的状态（伯努利采样）
            h_sample = self._sample_binary(h_prob)

            # 基于隐藏层的采样结果，重新估算可见层的激活概率（反向传播）
            v_prob = self._sigmoid(np.dot(h_sample, self.W.T) + self.b_v)

            # 根据估算的概率采样新的可见层状态
            v = self._sample_binary(v_prob)

        # 将最终的可见层向量重塑为 28×28 的图像格式
        return v.reshape(28, 28)

# 用MNIST 手写数字数据集训练一个（RBM），并从训练好的模型中采样生成一张手写数字图像
if __name__ == '__main__':
    try:
        mnist = np.load('mnist_bin.npy')  # 尝试加载文件
    except IOError:
        # 如果文件不存在或加载失败，生成新的二值化MNIST数据
        (train_images, _), (_, _) = mnist.load_data()  # 加载MNIST数据
        mnist_bin = (train_images >= 128).astype(np.int8)  # 二值化处理
        np.save('mnist_bin.npy', mnist_bin)  # 保存为.npy文件

        # 重新加载刚生成的文件
        mnist = np.load('mnist_bin.npy')
    except Exception as e:
        # 如果加载失败（其他错误，如文件损坏），保持原报错逻辑
        print("无法加载MNIST数据文件，请确保mnist_bin.npy文件在正确的路径下")
        print(f"错误详情: {e}")
        sys.exit(1)

    # 获取数据集的形状信息
    n_imgs, n_rows, n_cols = mnist.shape  # 分别表示图像数量、行数和列数
    img_size = n_rows * n_cols            # 计算单张图片展开后的长度

    # 打印数据集的形状信息，便于确认数据加载是否正确
    print(mnist.shape)  # 输出数据集的形状


    # 初始化 RBM 对象：2个隐藏节点，784个可见节点（28×28 图像）
    rbm = RBM(2, img_size)
    # 训练RBM
    errors = rbm.train(mnist, learning_rate=0.1, epochs=10, batch_size=100)
    # 生成并可视化样本
    samples = rbm.sample(n_samples=5, gibbs_steps=1000)
    # 使用 MNIST 数据进行训练
    rbm.train(mnist)

    # 从模型中采样一张图像
    s = rbm.sample()
