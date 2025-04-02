# HK_electricity_bill_calculator

# 电费和水费计算程序  这个程序用于计算同隔离屋之间的电费和水费分摊。它允许用户输入电表和水表读数，计算各自的使用量，并根据使用比例分摊费用。  

## 功能特点  - 计算电费分摊（按照用电量比例） - 可选择性地计算水费分摊 - 保存历史计算记录到SQLite数据库 - 查看历史计算记录 - 完整的输入验证和错误处理  

## 使用要求  - Python 3.6+ - SQLite3（Python标准库自带）

## 使用方法

1. 运行程序：
   ```
   python electricity_bill_calculator.py
   ```

2. 在主菜单中选择操作：
   - `1` - 计算新的账单
   - `2` - 查看历史记录
   - `3` - 退出程序

3. 计算新账单时，按照提示输入：
   - 你家和我家的电表读数（旧的和新的）
   - 总电费金额
   - 是否需要计算水费
   - 如需计算水费，输入水表读数和总水费金额

4. 程序会自动计算并显示：
   - 各自的用电量
   - 电费分摊金额
   - 水费分摊金额（如果选择计算水费）
   - 合计应付金额

## 数据存储

所有计算记录都会自动保存到名为 `utility_bills.db` 的SQLite数据库中，方便后续查询和统计。

## 错误处理

程序包含多种错误检查和异常处理机制：
- 检查输入是否为有效数字
- 确保新表读数大于旧表读数
- 检查费用金额的合理性
- 处理特大数值的确认 
