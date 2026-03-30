import React, { useState } from "react";
import { Link } from "wouter";
import { Search, MapPin, Box, ArrowRight, Tag } from "lucide-react";
import { Layout } from "@/components/Layout";
import { useListItems } from "@workspace/api-client-react";
import { CATEGORY_LABELS } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";

export default function Home() {
  const [searchQuery, setSearchQuery] = useState("");
  
  // Use a debounced search in a real app, but for simplicity here we query directly
  // In a production app with a large DB, we'd debounce the `q` param.
  const { data: items = [], isLoading } = useListItems(
    { q: searchQuery || undefined },
    { query: { enabled: true } }
  );

  return (
    <Layout>
      <div className="relative rounded-3xl overflow-hidden mb-12 bg-primary">
        <div 
          className="absolute inset-0 opacity-20 mix-blend-overlay"
          style={{ 
            backgroundImage: `url(${import.meta.env.BASE_URL}images/hero-bg.png)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          }}
        />
        <div className="relative px-6 py-20 sm:py-24 sm:px-12 flex flex-col items-center text-center">
          <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight mb-6 drop-shadow-md">
            물건을 찾는 가장 빠른 방법
          </h1>
          <p className="text-primary-foreground/80 text-lg max-w-2xl mb-10">
            StorageMap에 등록된 모든 물건의 위치를 5초 안에 확인하세요.
          </p>
          
          <div className="w-full max-w-2xl relative group">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <Search className="h-6 w-6 text-muted-foreground group-focus-within:text-primary transition-colors" />
            </div>
            <input
              type="text"
              className="w-full h-16 pl-14 pr-4 rounded-2xl bg-white text-lg text-foreground placeholder:text-muted-foreground shadow-xl focus:outline-none focus:ring-4 focus:ring-primary/30 transition-all"
              placeholder="물건 이름, 카테고리, 태그 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-foreground">
            {searchQuery ? `"${searchQuery}" 검색 결과` : "최근 등록된 물건"}
          </h2>
          <span className="text-sm font-medium text-muted-foreground bg-secondary px-3 py-1 rounded-full">
            {items.length}개 찾음
          </span>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-40 bg-secondary/50 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-2xl border border-dashed shadow-sm">
            <Box className="w-16 h-16 text-muted-foreground mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold text-foreground mb-2">검색 결과가 없습니다</h3>
            <p className="text-muted-foreground">다른 검색어를 입력하거나 새로운 물건을 등록해보세요.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  className="group bg-white rounded-2xl p-6 shadow-sm border hover:shadow-xl hover:border-primary/20 transition-all duration-300"
                >
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="text-lg font-bold text-foreground truncate pr-2">
                      {item.name}
                    </h3>
                    {item.category && (
                      <span className="shrink-0 text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary">
                        {CATEGORY_LABELS[item.category] || item.category}
                      </span>
                    )}
                  </div>
                  
                  <div className="bg-secondary/50 rounded-xl p-4 mb-4">
                    <div className="flex items-center text-sm font-medium text-foreground mb-2">
                      <MapPin className="w-4 h-4 text-primary mr-2" />
                      위치 경로
                    </div>
                    <div className="flex items-center flex-wrap gap-1.5 text-sm text-muted-foreground">
                      <span className="font-semibold text-foreground">{item.spaceName}</span>
                      <ArrowRight className="w-3 h-3" />
                      <Link 
                        href={`/spaces/${item.spaceId}/map`}
                        className="font-semibold text-primary hover:underline"
                      >
                        {item.furnitureName}
                      </Link>
                      {item.zoneName && (
                        <>
                          <ArrowRight className="w-3 h-3" />
                          <span>{item.zoneName}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {item.tags && item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {item.tags.map((tag, idx) => (
                        <span key={idx} className="inline-flex items-center text-xs bg-secondary text-secondary-foreground px-2 py-1 rounded-md">
                          <Tag className="w-3 h-3 mr-1 opacity-50" />
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-sm text-muted-foreground mt-auto pt-2 border-t border-border/50">
                    <span>수량: {item.quantity}개</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </Layout>
  );
}
