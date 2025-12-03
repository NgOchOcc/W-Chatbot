import json
import time
from typing import List, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pymilvus import Collection, connections
from transformers import AutoTokenizer


class MilvusTokenAnalyzer:
    def __init__(self, host="localhost", port="19530", collection_name="v768_cosine_2",
                 model_name="Qwen/Qwen2.5-7B-Instruct"):
        """
        Khởi tạo analyzer

        Args:
            host (str): Milvus host
            port (str): Milvus port
            collection_name (str): Tên collection
            model_name (str): Model tokenizer để sử dụng
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.model_name = model_name

        # Kết nối Milvus
        self.connect_milvus()

        # Khởi tạo tokenizer
        try:
            print(f"Đang tải tokenizer {model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.use_real_tokenizer = True
            print("✓ Tokenizer đã sẵn sàng!")
        except Exception as e:
            print(f"⚠ Không thể tải tokenizer thực: {e}")
            print("Sử dụng ước tính heuristic thay thế...")
            self.tokenizer = None
            self.use_real_tokenizer = False

    def connect_milvus(self):
        """Kết nối tới Milvus"""
        try:
            connections.connect("default", host=self.host, port=self.port)
            self.collection = Collection(name=self.collection_name)
            self.collection.load()
            print(f"✓ Đã kết nối Milvus: {self.collection_name}")
            print(f"✓ Schema: {self.collection.schema}")
            print(f"✓ Tổng số entities: {self.collection.num_entities}")
        except Exception as e:
            print(f"✗ Lỗi kết nối Milvus: {e}")
            raise

    def get_all_texts(self, batch_size=100) -> List[Dict]:
        print("Đang lấy dữ liệu từ Milvus...")
        all_docs = []
        offset = 0

        while True:
            try:
                # Query với limit và offset
                results = self.collection.query(
                    expr="",  # Lấy tất cả
                    output_fields=["id", "doc_id", "text"],
                    limit=batch_size,
                    offset=offset
                )

                if not results:
                    break

                all_docs.extend(results)
                offset += batch_size
                print(f"✓ Đã lấy {len(all_docs)} documents...")

                # Tránh vượt quá tổng số entities
                if len(results) < batch_size:
                    break

            except Exception as e:
                print(f"Lỗi khi lấy dữ liệu tại offset {offset}: {e}")
                break

        print(f"✓ Hoàn thành! Tổng cộng: {len(all_docs)} documents")
        return all_docs

    def count_tokens_real(self, text: str) -> int:
        """Đếm token sử dụng tokenizer thật"""
        try:
            tokens = self.tokenizer.encode(text, add_special_tokens=True)
            return len(tokens)
        except Exception as e:
            print(f"Lỗi tokenization: {e}")
            return self.count_tokens_heuristic(text)

    def count_tokens_heuristic(self, text: str) -> int:
        """Ước tính token count cho tiếng Romanian"""
        if not text or not text.strip():
            return 0

        words = text.split()
        base_tokens = len(words)

        # Điều chỉnh cho đặc trưng Romanian
        romanian_chars = "ăâîșțĂÂÎȘȚ"
        special_char_bonus = sum(1 for c in text if c in romanian_chars) * 0.15

        # Từ dài
        long_word_bonus = sum(0.4 for word in words if len(word.strip('.,;:!?()[]{}\"\'`-–—')) > 8)
        very_long_word_bonus = sum(0.3 for word in words if len(word.strip('.,;:!?()[]{}\"\'`-–—')) > 12)

        # Dấu câu
        punctuation_bonus = sum(1 for c in text if c in ".,;:!?()[]{}\"'`-–—") * 0.1

        # Complexity cho văn bản dài
        complexity_bonus = len(words) * 0.05 if len(words) > 50 else 0

        estimated = base_tokens + special_char_bonus + long_word_bonus + very_long_word_bonus + punctuation_bonus + complexity_bonus  # noqa
        return max(1, int(estimated))  # Ít nhất 1 token

    def analyze_single_document(self, doc: Dict) -> Dict:
        text = doc.get('text', '')

        # Đếm token
        if self.use_real_tokenizer:
            token_count = self.count_tokens_real(text)
        else:
            token_count = self.count_tokens_heuristic(text)

        # Phân tích cơ bản
        words = text.split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        # Ký tự đặc biệt Romanian
        romanian_chars = "ăâîșțĂÂÎȘȚ"
        romanian_char_count = sum(1 for c in text if c in romanian_chars)

        return {
            'id': doc.get('id', ''),
            'doc_id': doc.get('doc_id', ''),
            'text_preview': text[:100] + ('...' if len(text) > 100 else ''),
            'character_count': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'token_count': token_count,
            'tokens_per_word': token_count / len(words) if words else 0,
            'tokens_per_char': token_count / len(text) if text else 0,
            'avg_word_length': sum(len(w.strip('.,;:!?()[]{}\"\'`-–—')) for w in words) / len(words) if words else 0,
            'avg_sentence_length': len(words) / len(sentences) if sentences else 0,
            'romanian_char_count': romanian_char_count,
            'romanian_char_ratio': romanian_char_count / len(text) if text else 0,
            'text_length': len(text)
        }

    def analyze_all_documents(self) -> pd.DataFrame:
        print("\n=== BẮT ĐẦU PHÂN TÍCH TOKEN COUNT ===")

        # Lấy dữ liệu
        docs = self.get_all_texts()

        if not docs:
            print("Không có dữ liệu để phân tích!")
            return pd.DataFrame()

        # Phân tích từng document
        print(f"\nĐang phân tích {len(docs)} documents...")
        results = []

        start_time = time.time()
        for i, doc in enumerate(docs):
            if i % 50 == 0:
                elapsed = time.time() - start_time
                print(f"✓ Đã xử lý {i}/{len(docs)} documents ({elapsed:.1f}s)")

            analysis = self.analyze_single_document(doc)
            results.append(analysis)

        print(f"✓ Hoàn thành phân tích! ({time.time() - start_time:.1f}s)")

        # Tạo DataFrame
        df = pd.DataFrame(results)
        return df

    def calculate_statistics(self, df: pd.DataFrame) -> Dict:
        """Tính toán thống kê tổng hợp"""
        if df.empty:
            return {}

        token_stats = {
            'total_documents': len(df),
            'total_tokens': df['token_count'].sum(),
            'total_words': df['word_count'].sum(),
            'total_characters': df['character_count'].sum(),

            # Token statistics
            'token_min': df['token_count'].min(),
            'token_max': df['token_count'].max(),
            'token_mean': df['token_count'].mean(),
            'token_median': df['token_count'].median(),
            'token_std': df['token_count'].std(),
            'token_q25': df['token_count'].quantile(0.25),
            'token_q75': df['token_count'].quantile(0.75),
            'token_q90': df['token_count'].quantile(0.90),
            'token_q95': df['token_count'].quantile(0.95),
            'token_q99': df['token_count'].quantile(0.99),

            # Ratios
            'avg_tokens_per_word': df['tokens_per_word'].mean(),
            'avg_tokens_per_char': df['tokens_per_char'].mean(),
            'avg_word_length': df['avg_word_length'].mean(),
            'avg_sentence_length': df['avg_sentence_length'].mean(),

            # Romanian specific
            'avg_romanian_char_ratio': df['romanian_char_ratio'].mean(),

            # Distribution
            'short_docs': len(df[df['token_count'] < 100]),
            'medium_docs': len(df[(df['token_count'] >= 100) & (df['token_count'] < 500)]),
            'long_docs': len(df[df['token_count'] >= 500]),
        }

        return token_stats

    def print_statistics(self, stats: Dict):
        """In thống kê ra màn hình"""
        print("\n" + "=" * 60)
        print("           THỐNG KÊ TOKEN COUNT TỔNG HỢP")
        print("=" * 60)

        print("\n📊 TỔNG QUAN:")
        print(f"   • Tổng documents: {stats['total_documents']:,}")
        print(f"   • Tổng tokens: {stats['total_tokens']:,}")
        print(f"   • Tổng words: {stats['total_words']:,}")
        print(f"   • Tổng characters: {stats['total_characters']:,}")

        print("\n🎯 THỐNG KÊ TOKEN:")
        print(f"   • Min: {stats['token_min']:,} tokens")
        print(f"   • Max: {stats['token_max']:,} tokens")
        print(f"   • Mean: {stats['token_mean']:,.1f} tokens")
        print(f"   • Median: {stats['token_median']:,.1f} tokens")
        print(f"   • Std Dev: {stats['token_std']:,.1f}")
        print(f"   • Q25: {stats['token_q25']:,.1f}")
        print(f"   • Q75: {stats['token_q75']:,.1f}")
        print(f"   • Q90: {stats['token_q90']:,.1f}")
        print(f"   • Q95: {stats['token_q95']:,.1f}")
        print(f"   • Q99: {stats['token_q99']:,.1f}")

        print("\n📈 TỶ LỆ TRUNG BÌNH:")
        print(f"   • Tokens/Word: {stats['avg_tokens_per_word']:.3f}")
        print(f"   • Tokens/Char: {stats['avg_tokens_per_char']:.4f}")
        print(f"   • Độ dài TB từ: {stats['avg_word_length']:.1f} ký tự")
        print(f"   • Độ dài TB câu: {stats['avg_sentence_length']:.1f} từ")
        print(f"   • Tỷ lệ ký tự Romanian: {stats['avg_romanian_char_ratio']:.3f}")

        print("\n📋 PHÂN LOẠI THEO KÍCH THƯỚC:")
        print(
            f"   • Ngắn (<100 tokens): {stats['short_docs']:,} docs ({stats['short_docs'] / stats['total_documents'] * 100:.1f}%)")  # noqa
        print(
            f"   • Trung bình (100-499): {stats['medium_docs']:,} docs ({stats['medium_docs'] / stats['total_documents'] * 100:.1f}%)")  # noqa
        print(
            f"   • Dài (≥500 tokens): {stats['long_docs']:,} docs ({stats['long_docs'] / stats['total_documents'] * 100:.1f}%)")  # noqa

    def create_token_distribution_buckets(self, df: pd.DataFrame, bucket_size=100) -> Dict:
        if df.empty:
            return {}

        max_tokens = df['token_count'].max()

        # Tạo các bucket ranges
        bucket_ranges = []
        bucket_labels = []
        bucket_counts = []

        current = 0
        while current < max_tokens:
            next_val = current + bucket_size

            # Đếm documents trong bucket này
            count = len(df[(df['token_count'] >= current) & (df['token_count'] < next_val)])

            if count > 0:  # Chỉ thêm bucket có documents
                bucket_ranges.append((current, next_val))
                bucket_labels.append(f"{current}-{next_val - 1}")
                bucket_counts.append(count)

            current = next_val

        # Tạo phân bố chi tiết
        distribution = {}
        for i, (start, end) in enumerate(bucket_ranges):
            bucket_data = df[(df['token_count'] >= start) & (df['token_count'] < end)]
            distribution[bucket_labels[i]] = {
                'range': (start, end - 1),
                'count': bucket_counts[i],
                'percentage': bucket_counts[i] / len(df) * 100,
                'avg_tokens': bucket_data['token_count'].mean() if len(bucket_data) > 0 else 0,
                'avg_words': bucket_data['word_count'].mean() if len(bucket_data) > 0 else 0,
                'sample_doc_ids': bucket_data['doc_id'].head(3).tolist() if len(bucket_data) > 0 else []
            }

        return {
            'bucket_size': bucket_size,
            'total_buckets': len(bucket_ranges),
            'distribution': distribution,
            'bucket_labels': bucket_labels,
            'bucket_counts': bucket_counts,
            'bucket_ranges': bucket_ranges
        }

    def plot_token_distribution(self, df: pd.DataFrame, bucket_info: Dict, save_plot=True):
        try:
            # Set style
            plt.style.use('default')
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle('Token Count Distribution Analysis', fontsize=16, fontweight='bold')

            # 1. Histogram với buckets
            ax1.bar(bucket_info['bucket_labels'], bucket_info['bucket_counts'],
                    color='skyblue', alpha=0.7, edgecolor='navy')
            ax1.set_title('Token Distribution by Buckets', fontweight='bold')
            ax1.set_xlabel('Token Range')
            ax1.set_ylabel('Number of Documents')
            ax1.tick_params(axis='x', rotation=45)

            # Thêm annotation cho các bucket có nhiều documents
            for i, (label, count) in enumerate(zip(bucket_info['bucket_labels'], bucket_info['bucket_counts'])):
                if count > len(df) * 0.05:  # Hiển thị label nếu > 5% total
                    ax1.text(i, count + 0.5, str(count), ha='center', va='bottom')

            # 2. Cumulative distribution
            sorted_tokens = np.sort(df['token_count'])
            cumulative_pct = np.arange(1, len(sorted_tokens) + 1) / len(sorted_tokens) * 100
            ax2.plot(sorted_tokens, cumulative_pct, color='red', linewidth=2)
            ax2.set_title('Cumulative Distribution', fontweight='bold')
            ax2.set_xlabel('Token Count')
            ax2.set_ylabel('Cumulative Percentage')
            ax2.grid(True, alpha=0.3)

            # Thêm quantile lines
            quantiles = [0.5, 0.9, 0.95, 0.99]
            q_values = [df['token_count'].quantile(q) for q in quantiles]
            for q, val in zip(quantiles, q_values):
                ax2.axvline(val, color='orange', linestyle='--', alpha=0.7)
                ax2.text(val, q * 100, f'Q{int(q * 100)}: {val:.0f}', rotation=90,
                         verticalalignment='bottom', fontsize=9)

            # 3. Box plot
            ax3.boxplot(df['token_count'], vert=True, patch_artist=True,
                        boxprops=dict(facecolor='lightgreen', alpha=0.7))
            ax3.set_title('Token Count Box Plot', fontweight='bold')
            ax3.set_ylabel('Token Count')
            ax3.grid(True, alpha=0.3)

            # 4. Pie chart cho size categories
            sizes = [
                len(df[df['token_count'] < 100]),
                len(df[(df['token_count'] >= 100) & (df['token_count'] < 200)]),
                len(df[(df['token_count'] >= 200) & (df['token_count'] < 500)]),
                len(df[df['token_count'] >= 500])
            ]
            labels = ['<100 tokens', '100-199 tokens', '200-499 tokens', '≥500 tokens']
            colors = ['lightcoral', 'lightskyblue', 'lightgreen', 'plum']

            # Chỉ hiển thị categories có documents
            non_zero_sizes = [(size, label, color) for size, label, color in zip(sizes, labels, colors) if size > 0]
            if non_zero_sizes:
                sizes, labels, colors = zip(*non_zero_sizes)
                wedges, texts, autotexts = ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                                   startangle=90)
                ax4.set_title('Distribution by Size Categories', fontweight='bold')

            plt.tight_layout()

            if save_plot:
                plt.savefig('token_distribution.png', dpi=300, bbox_inches='tight')
                print("📊 Đã lưu biểu đồ: token_distribution.png")

            plt.show()

        except Exception as e:
            print(f"⚠ Lỗi khi vẽ biểu đồ: {e}")

    # def print_bucket_analysis(self, bucket_info: Dict):
    #     """In phân tích chi tiết theo bucket"""
    #     print(f"\n📊 PHÂN BỐ THEO BUCKET ({bucket_info['bucket_size']} tokens/bucket):")
    #     print("-" * 80)
    #
    #     total_docs = sum(bucket_info['bucket_counts'])
    #
    #     for label, data in bucket_info['distribution'].items():
    #         print(f"🔹 {label} tokens:")
    #         print(f"   • Số documents: {data['count']} ({data['percentage']:.1f}%)")
    #         print(f"   • TB tokens: {data['avg_tokens']:.1f}")
    #         print(f"   • TB words: {data['avg_words']:.1f}")
    #         if data['sample_doc_ids']:
    #             print(f"   • Mẫu doc_ids: {', '.join(data['sample_doc_ids'])}")
    #
    #     print(f"\n📈 TOP 5 BUCKET NHIỀU DOCUMENTS NHẤT:")
    #     sorted_buckets = sorted(bucket_info['distribution'].items(),
    #                             key=lambda x: x[1]['count'], reverse=True)[:5]
    #
    #     for i, (label, data) in enumerate(sorted_buckets, 1):
    #         print(f"   {i}. {label}: {data['count']} docs ({data['percentage']:.1f}%)")
    #
    #     """Tìm documents có token count cực trị"""
    #     print(f"\n🔝 TOP {n} DOCUMENTS DÀI NHẤT:")
    #     longest = df.nlargest(n, 'token_count')[
    #         ['doc_id', 'token_count', 'word_count', 'character_count', 'text_preview']]
    #     for i, row in longest.iterrows():
    #         print(f"   {row['doc_id']}: {row['token_count']} tokens, {row['word_count']} words")
    #         print(f"      Preview: {row['text_preview']}")
    #
    #     print(f"\n🔻 TOP {n} DOCUMENTS NGẮN NHẤT:")
    #     shortest = df.nsmallest(n, 'token_count')[
    #         ['doc_id', 'token_count', 'word_count', 'character_count', 'text_preview']]
    #     for i, row in shortest.iterrows():
    #         print(f"   {row['doc_id']}: {row['token_count']} tokens, {row['word_count']} words")
    #         print(f"      Preview: {row['text_preview']}")

    def save_results(self, df: pd.DataFrame, stats: Dict, bucket_info: Dict, filename_prefix="milvus_token_analysis"):
        """Lưu kết quả ra file"""
        try:
            # Lưu DataFrame
            csv_file = f"{filename_prefix}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8')
            print(f"\n💾 Đã lưu chi tiết: {csv_file}")

            # Lưu thống kê tổng hợp bao gồm bucket info
            stats_file = f"{filename_prefix}_stats.json"
            combined_stats = {**stats, 'bucket_analysis': bucket_info}

            with open(stats_file, 'w', encoding='utf-8') as f:
                # Convert numpy types to native Python types for JSON serialization
                json_stats = {}
                for k, v in combined_stats.items():
                    if isinstance(v, (np.integer, np.floating)):
                        json_stats[k] = v.item()
                    elif isinstance(v, dict):
                        json_stats[k] = {}
                        for k2, v2 in v.items():
                            if isinstance(v2, (np.integer, np.floating)):
                                json_stats[k][k2] = v2.item()
                            else:
                                json_stats[k][k2] = v2
                    else:
                        json_stats[k] = v

                json.dump(json_stats, f, ensure_ascii=False, indent=2)
            print(f"💾 Đã lưu thống kê: {stats_file}")

            # Lưu bucket distribution riêng
            bucket_file = f"{filename_prefix}_buckets.csv"
            bucket_df = pd.DataFrame([
                {
                    'bucket_range': label,
                    'start_token': data['range'][0],
                    'end_token': data['range'][1],
                    'doc_count': data['count'],
                    'percentage': data['percentage'],
                    'avg_tokens': data['avg_tokens'],
                    'avg_words': data['avg_words'],
                    'sample_docs': '; '.join(data['sample_doc_ids'])
                }
                for label, data in bucket_info['distribution'].items()
            ])
            bucket_df.to_csv(bucket_file, index=False, encoding='utf-8')
            print(f"💾 Đã lưu bucket analysis: {bucket_file}")

        except Exception as e:
            print(f"⚠ Lỗi khi lưu file: {e}")

    def run_full_analysis(self, save_results=True, bucket_size=100, create_plots=True):
        """Chạy phân tích đầy đủ"""
        print("🚀 BẮT ĐẦU PHÂN TÍCH ĐẦY ĐỦ MILVUS COLLECTION")
        print(f"📍 Collection: {self.collection_name}")
        print(f"🤖 Tokenizer: {'Real ' + self.model_name if self.use_real_tokenizer else 'Heuristic estimation'}")
        print(f"📊 Bucket size: {bucket_size} tokens")

        # Phân tích
        df = self.analyze_all_documents()

        if df.empty:
            print("❌ Không có dữ liệu để phân tích!")
            return None, None, None

        # Tính thống kê cơ bản
        stats = self.calculate_statistics(df)

        # Tạo bucket analysis
        bucket_info = self.create_token_distribution_buckets(df, bucket_size)

        # In kết quả
        self.print_statistics(stats)
        self.print_bucket_analysis(bucket_info)
        self.find_extremes(df)

        # Tạo biểu đồ
        if create_plots:
            self.plot_token_distribution(df, bucket_info, save_plot=save_results)

        # Lưu kết quả
        if save_results:
            self.save_results(df, stats, bucket_info)

        print("\n✅ HOÀN THÀNH PHÂN TÍCH!")
        return df, stats, bucket_info


# Sử dụng
if __name__ == "__main__":
    # Khởi tạo analyzer
    analyzer = MilvusTokenAnalyzer(
        host="localhost",
        port="19530",
        collection_name="v768_cosine_2",
        model_name="Qwen/Qwen2.5-7B-Instruct"
    )

    # Chạy phân tích đầy đủ với bucket size 100 tokens
    df, stats, bucket_info = analyzer.run_full_analysis(
        save_results=True,
        bucket_size=100,  # Có thể thay đổi: 50, 100, 200...
        create_plots=True
    )

    # Có thể sử dụng kết quả để phân tích thêm
    if df is not None and stats is not None:
        print("\n🔍 MỘT SỐ INSIGHT THÊM:")
        print(f"   • Document có nhiều token nhất: {df.loc[df['token_count'].idxmax(), 'doc_id']}")
        print(f"   • Document có ít token nhất: {df.loc[df['token_count'].idxmin(), 'doc_id']}")
        print(f"   • Tỷ lệ token/word cao nhất: {df['tokens_per_word'].max():.3f}")
        print(f"   • Tỷ lệ token/word thấp nhất: {df['tokens_per_word'].min():.3f}")

        # Context window analysis
        contexts = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
        print("\n📏 PHÂN TÍCH CONTEXT WINDOW:")
        for ctx in contexts:
            fitting_docs = len(df[df['token_count'] <= ctx])
            percentage = fitting_docs / len(df) * 100
            print(f"   • {ctx:,} tokens: {fitting_docs:,}/{len(df):,} docs ({percentage:.1f}%)")

        # Bucket insights
        if bucket_info and bucket_info['distribution']:
            print("\n🪣 BUCKET INSIGHTS:")
            print(f"   • Tổng số buckets có data: {bucket_info['total_buckets']}")

            # Tìm bucket có nhiều documents nhất
            max_bucket = max(bucket_info['distribution'].items(), key=lambda x: x[1]['count'])
            print(f"   • Bucket phổ biến nhất: {max_bucket[0]} ({max_bucket[1]['count']} docs)")

            # Tính phần trăm documents trong các bucket chính
            total_docs = sum([data['count'] for data in bucket_info['distribution'].values()])
            under_500 = sum([data['count'] for label, data in bucket_info['distribution'].items()
                             if data['range'][1] < 500])
            print(f"   • Documents < 500 tokens: {under_500}/{total_docs} ({under_500 / total_docs * 100:.1f}%)")

    print("\n📁 FILES GENERATED:")
    print("   • milvus_token_analysis.csv - Chi tiết từng document")
    print("   • milvus_token_analysis_stats.json - Thống kê tổng hợp")
    print("   • milvus_token_analysis_buckets.csv - Phân bố bucket")
    print("   • token_distribution.png - Biểu đồ phân bố")
