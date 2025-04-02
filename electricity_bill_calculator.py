import os
import sqlite3
import datetime
import re

class BillCalculator:
    def __init__(self, db_name="utility_bills.db"):
        self.db_name = db_name
        self.setup_database()
        
    def setup_database(self):
        """设置SQLite数据库"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bill_records'")
        table_exists = cursor.fetchone()
        
        # 创建表格（如果不存在）
        if not table_exists:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS bill_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                your_old_reading INTEGER,
                your_new_reading INTEGER,
                your_usage INTEGER,
                my_old_reading INTEGER,
                my_new_reading INTEGER,
                my_usage INTEGER,
                total_usage INTEGER,
                total_bill_amount REAL,
                your_share REAL,
                my_share REAL,
                water_calculated INTEGER,
                water_bill_amount REAL,
                your_water_share REAL,
                my_water_share REAL,
                your_old_water INTEGER,
                your_new_water INTEGER,
                your_water_usage INTEGER,
                my_old_water INTEGER,
                my_new_water INTEGER,
                my_water_usage INTEGER,
                total_water_usage INTEGER
            )
            ''')
        else:
            # 检查是否缺少水费相关列
            columns_to_check = [
                ('your_old_water', 'INTEGER'),
                ('your_new_water', 'INTEGER'),
                ('your_water_usage', 'INTEGER'),
                ('my_old_water', 'INTEGER'),
                ('my_new_water', 'INTEGER'),
                ('my_water_usage', 'INTEGER'),
                ('total_water_usage', 'INTEGER')
            ]
            
            # 获取当前表的所有列
            cursor.execute("PRAGMA table_info(bill_records)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # 添加缺少的列
            for column_name, column_type in columns_to_check:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE bill_records ADD COLUMN {column_name} {column_type}")
                        print(f"已添加列: {column_name}")
                    except Exception as e:
                        print(f"添加列时出错: {e}")
        
        conn.commit()
        conn.close()
        
    def validate_input(self, prompt, input_type="float", min_value=None, max_value=None, error_msg=None):
        """验证用户输入"""
        while True:
            try:
                user_input = input(prompt)
                
                # 检查是否为数字
                if input_type == "float":
                    value = float(user_input)
                elif input_type == "int":
                    value = int(user_input)
                elif input_type == "yn":
                    if user_input.lower() not in ['y', 'n']:
                        raise ValueError("请输入 Y 或 N")
                    return user_input.lower()
                
                # 检查范围
                if min_value is not None and value < min_value:
                    raise ValueError(f"输入值不能小于 {min_value}")
                if max_value is not None and value > max_value:
                    raise ValueError(f"输入值不能大于 {max_value}")
                
                return value
                
            except ValueError as e:
                print(error_msg if error_msg else f"输入错误: {e}")
    
    def check_meter_readings(self, old_reading, new_reading, meter_type="electric"):
        """检查表读数的合理性"""
        if new_reading < old_reading:
            raise ValueError("新表读数不能小于旧表读数")
        
        if meter_type == "electric":
            # 检查电表读数是否过小
            if new_reading < 1000 or old_reading < 1000:
                confirm = input("表读数似乎很小，是否继续？(Y/N): ").lower()
                if confirm != 'y':
                    raise ValueError("用户取消了操作")
        elif meter_type == "water":
            # 水表读数检查逻辑：个位数或太大才提示
            if new_reading < 10 or old_reading < 10 or new_reading > 100000 or old_reading > 100000:
                confirm = input("水表读数似乎不太合理，是否继续？(Y/N): ").lower()
                if confirm != 'y':
                    raise ValueError("用户取消了操作")
    
    def calculate_bills(self):
        """计算电费和水费"""
        print("\n===== 电费计算程序 =====")
        print("请输入电表读数和费用信息：")
        
        try:
            # 获取对方（你家）的电表读数
            your_old_reading = self.validate_input("你家的旧电表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
            your_new_reading = self.validate_input("你家的新电表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
            self.check_meter_readings(your_old_reading, your_new_reading, meter_type="electric")
            
            # 获取我家的电表读数
            my_old_reading = self.validate_input("我家的旧电表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
            my_new_reading = self.validate_input("我家的新电表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
            self.check_meter_readings(my_old_reading, my_new_reading, meter_type="electric")
            
            # 计算用电量
            your_usage = your_new_reading - your_old_reading
            my_usage = my_new_reading - my_old_reading
            total_usage = your_usage + my_usage
            
            print(f"\n你家: {your_new_reading}-{your_old_reading}={your_usage}")
            print(f"我家: {my_new_reading}-{my_old_reading}={my_usage}")
            print(f"总: {total_usage}")
            
            # 获取总电费金额
            total_bill_amount = self.validate_input("\n总电费金额($): ", min_value=0, error_msg="请输入有效的非负数")
            
            # 检查电费金额的合理性
            if total_bill_amount < 100 or total_bill_amount > 10000:
                confirm = input("电费金额似乎不太合理，是否继续？(Y/N): ").lower()
                if confirm != 'y':
                    raise ValueError("用户取消了操作")
            
            # 根据各自用电量占比计算应付费用
            your_share = round(total_bill_amount * your_usage / total_usage, 1) if total_usage > 0 else 0
            my_share = round(total_bill_amount * my_usage / total_usage, 1) if total_usage > 0 else 0
            
            # 确保合计等于总金额，调整四舍五入误差
            total_shares = round(your_share + my_share, 1)
            if abs(total_shares - total_bill_amount) > 0.01:
                diff = total_bill_amount - total_shares
                # 将差额分配给较大的份额，避免较小份额变成负数
                if your_usage >= my_usage:
                    your_share = round(your_share + diff, 1)
                else:
                    my_share = round(my_share + diff, 1)
            
            print(f"\n你家: {total_bill_amount:.1f}*{your_usage}/{total_usage}={your_share:.1f}")
            print(f"我家: {total_bill_amount:.1f}*{my_usage}/{total_usage}={my_share:.1f}")
            
            # 水费计算（可选）
            calculate_water = self.validate_input("\n是否需要计算水费？(Y/N): ", input_type="yn")
            
            water_bill_amount = 0
            your_water_share = 0
            my_water_share = 0
            water_calculated = 0
            your_old_water = 0
            your_new_water = 0
            my_old_water = 0
            my_new_water = 0
            your_water_usage = 0
            my_water_usage = 0
            total_water_usage = 0
            
            if calculate_water == 'y':
                water_calculated = 1
                print("\n===== 水费计算 =====")
                
                # 获取水费信息
                your_old_water = self.validate_input("你家的旧水表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
                your_new_water = self.validate_input("你家的新水表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
                self.check_meter_readings(your_old_water, your_new_water, meter_type="water")
                
                my_old_water = self.validate_input("我家的旧水表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
                my_new_water = self.validate_input("我家的新水表读数: ", input_type="int", min_value=0, error_msg="请输入有效的非负整数")
                self.check_meter_readings(my_old_water, my_new_water, meter_type="water")
                
                # 计算用水量
                your_water_usage = your_new_water - your_old_water
                my_water_usage = my_new_water - my_old_water
                total_water_usage = your_water_usage + my_water_usage
                
                print(f"\n你家: {your_new_water}-{your_old_water}={your_water_usage}")
                print(f"我家: {my_new_water}-{my_old_water}={my_water_usage}")
                print(f"总: {total_water_usage}")
                
                # 获取总水费金额
                water_bill_amount = self.validate_input("\n总水费金额($): ", min_value=0, error_msg="请输入有效的非负数")
                
                # 计算各自应付水费
                your_water_share = round(water_bill_amount * your_water_usage / total_water_usage, 1) if total_water_usage > 0 else 0
                my_water_share = round(water_bill_amount * my_water_usage / total_water_usage, 1) if total_water_usage > 0 else 0
                
                # 确保合计等于总金额，调整四舍五入误差
                total_water_shares = round(your_water_share + my_water_share, 1)
                if abs(total_water_shares - water_bill_amount) > 0.01:
                    diff = water_bill_amount - total_water_shares
                    # 将差额分配给较大的份额，避免较小份额变成负数
                    if your_water_usage >= my_water_usage:
                        your_water_share = round(your_water_share + diff, 1)
                    else:
                        my_water_share = round(my_water_share + diff, 1)
                
                print(f"\n你家水费: {water_bill_amount:.1f}*{your_water_usage}/{total_water_usage}={your_water_share:.1f}")
                print(f"我家水费: {water_bill_amount:.1f}*{my_water_usage}/{total_water_usage}={my_water_share:.1f}")
            
            # 显示结果
            self.display_results(
                your_old_reading, your_new_reading, your_usage,
                my_old_reading, my_new_reading, my_usage,
                total_usage, total_bill_amount, your_share, my_share,
                water_calculated, water_bill_amount, your_water_share, my_water_share,
                your_old_water, your_new_water, my_old_water, my_new_water,
                your_water_usage, my_water_usage, total_water_usage
            )
            
            # 保存记录到数据库
            self.save_to_database(
                your_old_reading, your_new_reading, your_usage,
                my_old_reading, my_new_reading, my_usage,
                total_usage, total_bill_amount, your_share, my_share,
                water_calculated, water_bill_amount, your_water_share, my_water_share,
                your_old_water, your_new_water, your_water_usage,
                my_old_water, my_new_water, my_water_usage, total_water_usage
            )
            
        except ValueError as e:
            print(f"错误: {e}")
        except Exception as e:
            print(f"发生错误: {e}")
            import traceback
            traceback.print_exc()
    
    def display_results(self, your_old_reading, your_new_reading, your_usage,
                       my_old_reading, my_new_reading, my_usage,
                       total_usage, total_bill_amount, your_share, my_share,
                       water_calculated, water_bill_amount, your_water_share, my_water_share,
                       your_old_water, your_new_water, my_old_water, my_new_water,
                       your_water_usage, my_water_usage, total_water_usage):
        """显示计算结果"""
        print("\n📊 *电费水费计算结果* 📊")
        print("-"*30)
        
        print("\n⚡ *电费分摊* ⚡")
        print("📝 表读数:")
        print(f"你家: {your_old_reading} → {your_new_reading}")
        print(f"我家: {my_old_reading} → {my_new_reading}")
        
        print("\n📈 用电量:")
        print(f"你家: {your_usage} 度")
        print(f"我家: {my_usage} 度")
        print(f"总用电: {total_usage} 度")
        
        # 计算比例
        your_percent = (your_usage / total_usage * 100) if total_usage > 0 else 0
        my_percent = (my_usage / total_usage * 100) if total_usage > 0 else 0
        
        print(f"\n💰 总电费: ${total_bill_amount:.1f}")
        print("\n📊 分摊比例:")
        print(f"你家: {your_percent:.1f}% ({your_usage}/{total_usage})")
        print(f"我家: {my_percent:.1f}% ({my_usage}/{total_usage})")
        
        print("\n💵 分摊金额:")
        print(f"你家电费: ${your_share:.1f}")
        print(f"我家电费: ${my_share:.1f}")
        
        total_your_share = your_share
        total_my_share = my_share
        
        if water_calculated:
            print("\n💧 *水费分摊* 💧")
            print("📝 表读数:")
            print(f"你家: {your_old_water} → {your_new_water}")
            print(f"我家: {my_old_water} → {my_new_water}")
            
            print("\n📈 用水量:")
            print(f"你家: {your_water_usage} 单位")
            print(f"我家: {my_water_usage} 单位")
            print(f"总用水: {total_water_usage} 单位")
            
            # 计算水费比例
            your_water_percent = (your_water_usage / total_water_usage * 100) if total_water_usage > 0 else 0
            my_water_percent = (my_water_usage / total_water_usage * 100) if total_water_usage > 0 else 0
            
            print(f"\n💰 总水费: ${water_bill_amount:.1f}")
            print("\n📊 分摊比例:")
            print(f"你家: {your_water_percent:.1f}% ({your_water_usage}/{total_water_usage})")
            print(f"我家: {my_water_percent:.1f}% ({my_water_usage}/{total_water_usage})")
            
            print("\n💵 分摊金额:")
            print(f"你家水费: ${your_water_share:.1f}")
            print(f"我家水费: ${my_water_share:.1f}")
            
            total_your_share += your_water_share
            total_my_share += my_water_share
        
        print("\n💵 *总费用* 💵")
        if water_calculated:
            print(f"你家总计: ${total_your_share:.1f} (电费 ${your_share:.1f} + 水费 ${your_water_share:.1f})")
            print(f"我家总计: ${total_my_share:.1f} (电费 ${my_share:.1f} + 水费 ${my_water_share:.1f})")
        else:
            print(f"你家总计: ${total_your_share:.1f}")
            print(f"我家总计: ${total_my_share:.1f}")
        print("-"*30)
    
    def save_to_database(self, your_old_reading, your_new_reading, your_usage,
                       my_old_reading, my_new_reading, my_usage,
                       total_usage, total_bill_amount, your_share, my_share,
                       water_calculated, water_bill_amount, your_water_share, my_water_share,
                       your_old_water=0, your_new_water=0, your_water_usage=0,
                       my_old_water=0, my_new_water=0, my_water_usage=0, total_water_usage=0):
        """保存记录到数据库"""
        try:
            print("\n正在保存计算结果到数据库...")
            
            # 验证数据正确性
            # 1. 验证用电量是否与读数一致
            calc_your_usage = your_new_reading - your_old_reading
            calc_my_usage = my_new_reading - my_old_reading
            
            if calc_your_usage != your_usage:
                print(f"警告: 你家用电量不一致 (计算值:{calc_your_usage}, 传入值:{your_usage})")
                your_usage = calc_your_usage
            
            if calc_my_usage != my_usage:
                print(f"警告: 我家用电量不一致 (计算值:{calc_my_usage}, 传入值:{my_usage})")
                my_usage = calc_my_usage
            
            if your_usage + my_usage != total_usage:
                print(f"警告: 总用电量不一致 (计算值:{your_usage + my_usage}, 传入值:{total_usage})")
                total_usage = your_usage + my_usage
            
            # 2. 确保总电费不为0并且分摊金额与百分比一致
            if total_bill_amount <= 0:
                print(f"警告: 总电费为 ${total_bill_amount}，这可能是错误的")
                if total_usage > 0:
                    print("请检查电费数据")
            
            # 3. 验证电费分摊
            if total_usage > 0:
                expected_your_share = round(total_bill_amount * your_usage / total_usage, 1)
                expected_my_share = round(total_bill_amount * my_usage / total_usage, 1)
                
                # 修正四舍五入误差
                if abs(expected_your_share + expected_my_share - total_bill_amount) > 0.1:
                    diff = total_bill_amount - (expected_your_share + expected_my_share)
                    if your_usage >= my_usage:
                        expected_your_share = round(expected_your_share + diff, 1)
                    else:
                        expected_my_share = round(expected_my_share + diff, 1)
                
                if abs(your_share - expected_your_share) > 0.1:
                    print(f"警告: 你家电费分摊不一致 (应为:{expected_your_share}, 传入值:{your_share})")
                    your_share = expected_your_share
                
                if abs(my_share - expected_my_share) > 0.1:
                    print(f"警告: 我家电费分摊不一致 (应为:{expected_my_share}, 传入值:{my_share})")
                    my_share = expected_my_share
            
            # 4. 如果计算了水费，验证水费相关数据
            if water_calculated:
                # 验证用水量是否与读数一致
                calc_your_water_usage = your_new_water - your_old_water
                calc_my_water_usage = my_new_water - my_old_water
                
                # 检查水表读数是否可能颠倒了
                if calc_your_water_usage < 0 and your_water_usage > 0:
                    print(f"警告: 你家水表读数可能颠倒了 (旧:{your_old_water}, 新:{your_new_water})")
                    temp = your_old_water
                    your_old_water = your_new_water
                    your_new_water = temp
                    calc_your_water_usage = your_new_water - your_old_water
                
                if calc_my_water_usage < 0 and my_water_usage > 0:
                    print(f"警告: 我家水表读数可能颠倒了 (旧:{my_old_water}, 新:{my_new_water})")
                    temp = my_old_water
                    my_old_water = my_new_water
                    my_new_water = temp
                    calc_my_water_usage = my_new_water - my_old_water
                
                if calc_your_water_usage != your_water_usage:
                    print(f"警告: 你家用水量不一致 (计算值:{calc_your_water_usage}, 传入值:{your_water_usage})")
                    your_water_usage = calc_your_water_usage
                
                if calc_my_water_usage != my_water_usage:
                    print(f"警告: 我家用水量不一致 (计算值:{calc_my_water_usage}, 传入值:{my_water_usage})")
                    my_water_usage = calc_my_water_usage
                
                if your_water_usage + my_water_usage != total_water_usage:
                    print(f"警告: 总用水量不一致 (计算值:{your_water_usage + my_water_usage}, 传入值:{total_water_usage})")
                    total_water_usage = your_water_usage + my_water_usage
                
                # 验证水费分摊
                if total_water_usage > 0:
                    expected_your_water_share = round(water_bill_amount * your_water_usage / total_water_usage, 1)
                    expected_my_water_share = round(water_bill_amount * my_water_usage / total_water_usage, 1)
                    
                    # 修正四舍五入误差
                    if abs(expected_your_water_share + expected_my_water_share - water_bill_amount) > 0.1:
                        diff = water_bill_amount - (expected_your_water_share + expected_my_water_share)
                        if your_water_usage >= my_water_usage:
                            expected_your_water_share = round(expected_your_water_share + diff, 1)
                        else:
                            expected_my_water_share = round(expected_my_water_share + diff, 1)
                    
                    if abs(your_water_share - expected_your_water_share) > 0.1:
                        print(f"警告: 你家水费分摊不一致 (应为:{expected_your_water_share}, 传入值:{your_water_share})")
                        your_water_share = expected_your_water_share
                    
                    if abs(my_water_share - expected_my_water_share) > 0.1:
                        print(f"警告: 我家水费分摊不一致 (应为:{expected_my_water_share}, 传入值:{my_water_share})")
                        my_water_share = expected_my_water_share
            
            # 连接数据库
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # 转换为正确的数据类型
            your_old_reading = int(your_old_reading)
            your_new_reading = int(your_new_reading)
            your_usage = int(your_usage)
            my_old_reading = int(my_old_reading)
            my_new_reading = int(my_new_reading)
            my_usage = int(my_usage)
            total_usage = int(total_usage)
            total_bill_amount = float(total_bill_amount)
            your_share = float(your_share)
            my_share = float(my_share)
            water_calculated = int(water_calculated)
            water_bill_amount = float(water_bill_amount)
            your_water_share = float(your_water_share)
            my_water_share = float(my_water_share)
            your_old_water = int(your_old_water)
            your_new_water = int(your_new_water)
            your_water_usage = int(your_water_usage)
            my_old_water = int(my_old_water)
            my_new_water = int(my_new_water)
            my_water_usage = int(my_water_usage)
            total_water_usage = int(total_water_usage)
            
            # 使用参数化查询防止SQL注入
            cursor.execute('''
            INSERT INTO bill_records (
                date, your_old_reading, your_new_reading, your_usage,
                my_old_reading, my_new_reading, my_usage,
                total_usage, total_bill_amount, your_share, my_share,
                water_calculated, water_bill_amount, your_water_share, my_water_share,
                your_old_water, your_new_water, your_water_usage,
                my_old_water, my_new_water, my_water_usage, total_water_usage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                your_old_reading, your_new_reading, your_usage,
                my_old_reading, my_new_reading, my_usage,
                total_usage, total_bill_amount, your_share, my_share,
                water_calculated, water_bill_amount, your_water_share, my_water_share,
                your_old_water, your_new_water, your_water_usage,
                my_old_water, my_new_water, my_water_usage, total_water_usage
            ))
            
            # 获取刚插入的记录ID
            record_id = cursor.lastrowid
            conn.commit()
            
            print(f"计算记录已成功保存到数据库 (ID: {record_id})")
            
        except Exception as e:
            print(f"保存到数据库时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    def view_history(self):
        """查看历史记录"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # 查询所有记录
            cursor.execute("SELECT * FROM bill_records ORDER BY date DESC")
            records = cursor.fetchall()
            
            if not records:
                print("没有找到历史记录")
                return
            
            # 分页设置
            page_size = 2  # 每页显示2条记录
            total_records = len(records)
            total_pages = (total_records + page_size - 1) // page_size  # 向上取整
            current_page = 1
            
            while True:
                self.clear_screen()  # 清屏函数
                start_idx = (current_page - 1) * page_size
                end_idx = min(start_idx + page_size, total_records)
                
                print(f"\n📜 *历史记录* 📜 (第{current_page}/{total_pages}页)")
                
                # 显示当前页的记录
                for i in range(start_idx, end_idx):
                    record = records[i]
                    try:
                        # 提取记录ID和日期
                        record_id = record[0]
                        record_date = record[1] if record[1] is not None else "未知日期"
                        print("\n" + "-"*30)
                        print(f"📅 {record_date} [ID: {record_id}]")
                        
                        # 直接从数据库获取电费相关数据，处理可能的None值
                        try:
                            your_old_reading = int(record[2]) if record[2] is not None else 0
                            your_new_reading = int(record[3]) if record[3] is not None else 0
                            your_usage = int(record[4]) if record[4] is not None else 0
                            my_old_reading = int(record[5]) if record[5] is not None else 0
                            my_new_reading = int(record[6]) if record[6] is not None else 0
                            my_usage = int(record[7]) if record[7] is not None else 0
                            total_usage = int(record[8]) if record[8] is not None else 0
                            total_bill_amount = float(record[9]) if record[9] is not None else 0.0
                            your_share = float(record[10]) if record[10] is not None else 0.0
                            my_share = float(record[11]) if record[11] is not None else 0.0
                            
                            # 验证并修正用电量，确保与表读数一致
                            calc_your_usage = your_new_reading - your_old_reading
                            calc_my_usage = my_new_reading - my_old_reading
                            
                            if your_usage != calc_your_usage or your_usage <= 0:
                                your_usage = max(0, calc_your_usage)
                            if my_usage != calc_my_usage or my_usage <= 0:
                                my_usage = max(0, calc_my_usage)
                            if total_usage != your_usage + my_usage:
                                total_usage = your_usage + my_usage
                            
                            # 如果总电费有效但分摊金额不一致，重新计算分摊
                            if total_bill_amount > 0 and total_usage > 0:
                                expected_your_share = round(total_bill_amount * your_usage / total_usage, 1)
                                expected_my_share = round(total_bill_amount * my_usage / total_usage, 1)
                                
                                # 修正四舍五入误差
                                if round(expected_your_share + expected_my_share, 1) != total_bill_amount:
                                    diff = total_bill_amount - round(expected_your_share + expected_my_share, 1)
                                    if your_usage >= my_usage:
                                        expected_your_share = round(expected_your_share + diff, 1)
                                    else:
                                        expected_my_share = round(expected_my_share + diff, 1)
                                
                                # 如果分摊金额与预期不符，使用重新计算的值
                                if abs(your_share - expected_your_share) > 0.1 or abs(my_share - expected_my_share) > 0.1:
                                    your_share = expected_your_share
                                    my_share = expected_my_share
                            
                            # 显示电费分摊结果
                            print("\n⚡ *电费分摊* ⚡")
                            print("📝 表读数:")
                            print(f"你家: {your_old_reading} → {your_new_reading}")
                            print(f"我家: {my_old_reading} → {my_new_reading}")
                            
                            print("\n📈 用电量:")
                            print(f"你家: {your_usage} 度")
                            print(f"我家: {my_usage} 度")
                            print(f"总用电: {total_usage} 度")
                            
                            # 计算电费占比，防止除以零错误
                            if total_usage > 0:
                                your_percent = (your_usage / total_usage * 100)
                                my_percent = (my_usage / total_usage * 100)
                            else:
                                your_percent = 0.0
                                my_percent = 0.0
                            
                            print(f"\n💰 总电费: ${total_bill_amount:.1f}")
                            print("\n📊 分摊比例:")
                            print(f"你家: {your_percent:.1f}% ({your_usage}/{total_usage})")
                            print(f"我家: {my_percent:.1f}% ({my_usage}/{total_usage})")
                            
                            print("\n💵 分摊金额:")
                            print(f"你家电费: ${your_share:.1f}")
                            print(f"我家电费: ${my_share:.1f}")
                            
                            total_your_share = your_share
                            total_my_share = my_share
                            
                            # 水费部分
                            water_calculated = int(record[12]) if record[12] is not None else 0
                            
                            if water_calculated:
                                try:
                                    water_bill_amount = float(record[13]) if record[13] is not None else 0.0
                                    your_water_share = float(record[14]) if record[14] is not None else 0.0
                                    my_water_share = float(record[15]) if record[15] is not None else 0.0
                                    
                                    your_old_water = int(record[16]) if record[16] is not None else 0
                                    your_new_water = int(record[17]) if record[17] is not None else 0
                                    your_water_usage = int(record[18]) if record[18] is not None else 0
                                    my_old_water = int(record[19]) if record[19] is not None else 0
                                    my_new_water = int(record[20]) if record[20] is not None else 0
                                    my_water_usage = int(record[21]) if record[21] is not None else 0
                                    total_water_usage = int(record[22]) if record[22] is not None else 0
                                    
                                    # 验证并修正用水量，确保与表读数一致
                                    calc_your_water_usage = your_new_water - your_old_water
                                    calc_my_water_usage = my_new_water - my_old_water
                                    
                                    # 如果数据异常，可能是新旧读数颠倒了
                                    if calc_your_water_usage < 0 and your_water_usage > 0:
                                        # 交换新旧读数
                                        temp = your_old_water
                                        your_old_water = your_new_water
                                        your_new_water = temp
                                        calc_your_water_usage = your_new_water - your_old_water
                                    
                                    if calc_my_water_usage < 0 and my_water_usage > 0:
                                        # 交换新旧读数
                                        temp = my_old_water
                                        my_old_water = my_new_water
                                        my_new_water = temp
                                        calc_my_water_usage = my_new_water - my_old_water
                                    
                                    if your_water_usage != calc_your_water_usage or your_water_usage < 0:
                                        your_water_usage = max(0, calc_your_water_usage)
                                    if my_water_usage != calc_my_water_usage or my_water_usage < 0:
                                        my_water_usage = max(0, calc_my_water_usage)
                                    if total_water_usage != your_water_usage + my_water_usage:
                                        total_water_usage = your_water_usage + my_water_usage
                                    
                                    # 如果总水费有效但分摊金额不一致，重新计算分摊
                                    if water_bill_amount > 0 and total_water_usage > 0:
                                        expected_your_water_share = round(water_bill_amount * your_water_usage / total_water_usage, 1)
                                        expected_my_water_share = round(water_bill_amount * my_water_usage / total_water_usage, 1)
                                        
                                        # 修正四舍五入误差
                                        if round(expected_your_water_share + expected_my_water_share, 1) != water_bill_amount:
                                            diff = water_bill_amount - round(expected_your_water_share + expected_my_water_share, 1)
                                            if your_water_usage >= my_water_usage:
                                                expected_your_water_share = round(expected_your_water_share + diff, 1)
                                            else:
                                                expected_my_water_share = round(expected_my_water_share + diff, 1)
                                        
                                        # 如果分摊金额与预期不符，使用重新计算的值
                                        if abs(your_water_share - expected_your_water_share) > 0.1 or abs(my_water_share - expected_my_water_share) > 0.1:
                                            your_water_share = expected_your_water_share
                                            my_water_share = expected_my_water_share
                                    
                                    print("\n💧 *水费分摊* 💧")
                                    print("📝 表读数:")
                                    print(f"你家: {your_old_water} → {your_new_water}")
                                    print(f"我家: {my_old_water} → {my_new_water}")
                                    
                                    print("\n📈 用水量:")
                                    print(f"你家: {your_water_usage} 单位")
                                    print(f"我家: {my_water_usage} 单位")
                                    print(f"总用水: {total_water_usage} 单位")
                                    
                                    # 计算水费占比，防止除以零错误
                                    if total_water_usage > 0:
                                        your_water_percent = (your_water_usage / total_water_usage * 100)
                                        my_water_percent = (my_water_usage / total_water_usage * 100)
                                    else:
                                        your_water_percent = 0.0
                                        my_water_percent = 0.0
                                    
                                    print(f"\n💰 总水费: ${water_bill_amount:.1f}")
                                    print("\n📊 分摊比例:")
                                    print(f"你家: {your_water_percent:.1f}% ({your_water_usage}/{total_water_usage})")
                                    print(f"我家: {my_water_percent:.1f}% ({my_water_usage}/{total_water_usage})")
                                    
                                    print("\n💵 分摊金额:")
                                    print(f"你家水费: ${your_water_share:.1f}")
                                    print(f"我家水费: ${my_water_share:.1f}")
                                    
                                    total_your_share += your_water_share
                                    total_my_share += my_water_share
                                except Exception as e:
                                    print(f"处理水费数据时出错: {e}")
                                    print("水费数据显示失败，可能数据不完整")
                            
                            # 显示总费用
                            print("\n💵 *总费用* 💵")
                            if water_calculated:
                                print(f"你家总计: ${total_your_share:.1f} (电费 ${your_share:.1f} + 水费 ${your_water_share:.1f})")
                                print(f"我家总计: ${total_my_share:.1f} (电费 ${my_share:.1f} + 水费 ${my_water_share:.1f})")
                            else:
                                print(f"你家总计: ${total_your_share:.1f}")
                                print(f"我家总计: ${total_my_share:.1f}")
                        except Exception as e:
                            print(f"处理电费数据时出错: {e}")
                            print("此记录数据不完整，建议使用'F'选项修复此记录或删除")
                        
                    except Exception as e:
                        print(f"显示记录 {record_id} 时出错: {e}")
                        print(f"此记录可能有错误，请使用'F'选项修复或删除")
                        continue
                
                # 分页导航
                print("\n" + "-"*30)
                print("[P] 上一页 | [N] 下一页 | [数字] 跳到特定页 | [Q] 返回主菜单 | [F] 修复当前页记录 | [D] 删除记录")
                
                choice = input("请选择: ").lower()
                
                if choice == 'q':
                    break
                elif choice == 'p' and current_page > 1:
                    current_page -= 1
                elif choice == 'n' and current_page < total_pages:
                    current_page += 1
                elif choice == 'f':
                    # 修复当前页上的记录
                    for i in range(start_idx, end_idx):
                        record_id = records[i][0]
                        try:
                            # 确认是否要修复此记录
                            fix_confirm = input(f"是否要修复记录ID: {record_id}? (y/n): ").lower()
                            if fix_confirm == 'y':
                                self.fix_record(record_id)
                        except Exception as e:
                            print(f"修复记录 {record_id} 时出错: {e}")
                    # 重新加载记录
                    cursor.execute("SELECT * FROM bill_records ORDER BY date DESC")
                    records = cursor.fetchall()
                elif choice == 'd':
                    # 删除记录
                    record_id = input("请输入要删除的记录ID: ")
                    try:
                        record_id = int(record_id)
                        delete_confirm = input(f"确认要删除记录ID: {record_id}? (y/n): ").lower()
                        if delete_confirm == 'y':
                            cursor.execute("DELETE FROM bill_records WHERE id = ?", (record_id,))
                            conn.commit()
                            print(f"记录ID: {record_id} 已删除")
                            # 重新加载记录
                            cursor.execute("SELECT * FROM bill_records ORDER BY date DESC")
                            records = cursor.fetchall()
                            total_records = len(records)
                            total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 1
                            current_page = min(current_page, total_pages) if total_pages > 0 else 1
                    except ValueError:
                        print("请输入有效的记录ID")
                elif choice.isdigit():
                    page_num = int(choice)
                    if 1 <= page_num <= total_pages:
                        current_page = page_num
                    else:
                        print(f"页码超出范围，请输入1-{total_pages}之间的数字")
                        input("按Enter键继续...")
                else:
                    print("无效选择，请重试")
                    input("按Enter键继续...")
            
        except Exception as e:
            print(f"查看历史记录时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()
                
    def fix_record(self, record_id):
        """修复特定记录的错误数据"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # 查询记录
            cursor.execute("SELECT * FROM bill_records WHERE id = ?", (record_id,))
            record = cursor.fetchone()
            
            if not record:
                print(f"找不到ID为 {record_id} 的记录")
                return
                
            print(f"正在修复记录ID: {record_id}")
            
            # 获取所有字段值
            your_old_reading = int(record[2]) if record[2] is not None else 0
            your_new_reading = int(record[3]) if record[3] is not None else 0
            your_usage = your_new_reading - your_old_reading
            my_old_reading = int(record[5]) if record[5] is not None else 0
            my_new_reading = int(record[6]) if record[6] is not None else 0
            my_usage = my_new_reading - my_old_reading
            total_usage = your_usage + my_usage
            
            total_bill_amount = float(record[9]) if record[9] is not None else 0.0
            
            # 如果总电费为0，请求用户输入
            if total_bill_amount <= 0:
                try:
                    total_bill_amount = float(input("请输入正确的总电费金额: "))
                except ValueError:
                    print("输入无效，设置为默认值641.0")
                    total_bill_amount = 641.0
            
            # 重新计算分摊金额
            your_share = round(total_bill_amount * your_usage / total_usage, 1) if total_usage > 0 else 0
            my_share = round(total_bill_amount * my_usage / total_usage, 1) if total_usage > 0 else 0
            
            # 水费部分
            water_calculated = int(record[12]) if record[12] is not None else 0
            water_bill_amount = float(record[13]) if record[13] is not None else 0.0
            
            if water_calculated:
                your_old_water = int(record[16]) if record[16] is not None else 0
                your_new_water = int(record[17]) if record[17] is not None else 0
                your_water_usage = your_new_water - your_old_water
                my_old_water = int(record[19]) if record[19] is not None else 0
                my_new_water = int(record[20]) if record[20] is not None else 0
                my_water_usage = my_new_water - my_old_water
                
                # 如果水表读数不合理，请求用户输入
                if your_water_usage <= 0 or my_water_usage < 0:
                    print("水表读数异常，请输入正确的数值:")
                    try:
                        your_old_water = int(input("你家的旧水表读数: "))
                        your_new_water = int(input("你家的新水表读数: "))
                        your_water_usage = your_new_water - your_old_water
                        
                        my_old_water = int(input("我家的旧水表读数: "))
                        my_new_water = int(input("我家的新水表读数: "))
                        my_water_usage = my_new_water - my_old_water
                    except ValueError:
                        print("输入无效，使用默认值")
                        your_old_water = 644
                        your_new_water = 770
                        your_water_usage = 126
                        my_old_water = 163
                        my_new_water = 164
                        my_water_usage = 1
                
                total_water_usage = your_water_usage + my_water_usage
                
                # 如果总水费为0，请求用户输入
                if water_bill_amount <= 0:
                    try:
                        water_bill_amount = float(input("请输入正确的总水费金额: "))
                    except ValueError:
                        print("输入无效，设置为默认值733.8")
                        water_bill_amount = 733.8
                
                # 重新计算水费分摊
                your_water_share = round(water_bill_amount * your_water_usage / total_water_usage, 1) if total_water_usage > 0 else 0
                my_water_share = round(water_bill_amount * my_water_usage / total_water_usage, 1) if total_water_usage > 0 else 0
            else:
                your_old_water = 0
                your_new_water = 0
                your_water_usage = 0
                my_old_water = 0
                my_new_water = 0
                my_water_usage = 0
                total_water_usage = 0
                water_bill_amount = 0
                your_water_share = 0
                my_water_share = 0
            
            # 更新记录
            cursor.execute('''
            UPDATE bill_records SET
                your_old_reading = ?,
                your_new_reading = ?,
                your_usage = ?,
                my_old_reading = ?,
                my_new_reading = ?,
                my_usage = ?,
                total_usage = ?,
                total_bill_amount = ?,
                your_share = ?,
                my_share = ?,
                water_calculated = ?,
                water_bill_amount = ?,
                your_water_share = ?,
                my_water_share = ?,
                your_old_water = ?,
                your_new_water = ?,
                your_water_usage = ?,
                my_old_water = ?,
                my_new_water = ?,
                my_water_usage = ?,
                total_water_usage = ?
            WHERE id = ?
            ''', (
                your_old_reading,
                your_new_reading,
                your_usage,
                my_old_reading,
                my_new_reading,
                my_usage,
                total_usage,
                total_bill_amount,
                your_share,
                my_share,
                water_calculated,
                water_bill_amount,
                your_water_share,
                my_water_share,
                your_old_water,
                your_new_water,
                your_water_usage,
                my_old_water,
                my_new_water,
                my_water_usage,
                total_water_usage,
                record_id
            ))
            
            conn.commit()
            print(f"记录 {record_id} 已成功修复")
            
        except Exception as e:
            print(f"修复记录时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    def display_menu(self):
        """显示主菜单"""
        while True:
            self.clear_screen()
            print("\n📊 *电费水费计算系统* 📊")
            print("\n请选择功能:")
            print("1. 计算电费和水费")
            print("2. 查看历史记录")
            print("0. 退出程序")
            
            choice = input("\n请输入选项编号: ")
            
            if choice == '1':
                self.calculate_bills()
                input("\n按Enter键返回主菜单...")
            elif choice == '2':
                self.view_history()
            elif choice == '0':
                print("\n感谢使用电费计算程序，再见！")
                break
            else:
                print("无效选择，请重试。")
                input("\n按Enter键继续...")
                
    def clear_screen(self):
        """清除屏幕内容"""
        if os.name == 'nt':  # Windows
            os.system('cls')
        else:  # Mac/Linux
            os.system('clear')

def main():
    calculator = BillCalculator()
    
    calculator.display_menu()

if __name__ == "__main__":
    main() 