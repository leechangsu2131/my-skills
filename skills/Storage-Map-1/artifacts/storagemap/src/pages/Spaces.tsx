import React, { useState } from "react";
import { Link } from "wouter";
import { Layout } from "@/components/Layout";
import { EmptyState } from "@/components/EmptyState";
import { useListSpaces } from "@workspace/api-client-react";
import { useCreateSpaceMutation, useDeleteSpaceMutation } from "@/hooks/use-spaces-wrapper";
import { SPACE_CONTEXT_LABELS } from "@/lib/utils";
import { Map, Plus, Building, Home, School, Trash2 } from "lucide-react";
import { motion } from "framer-motion";

export default function Spaces() {
  const { data: spaces = [], isLoading } = useListSpaces();
  const createMutation = useCreateSpaceMutation();
  const deleteMutation = useDeleteSpaceMutation();
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({ name: "", context: "home" as any, description: "" });

  const getContextIcon = (context?: string | null) => {
    if (context === 'office') return <Building className="w-5 h-5" />;
    if (context === 'classroom') return <School className="w-5 h-5" />;
    return <Home className="w-5 h-5" />;
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    
    createMutation.mutate({ data: formData }, {
      onSuccess: () => {
        setIsDialogOpen(false);
        setFormData({ name: "", context: "home", description: "" });
      }
    });
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    if (confirm("정말로 이 공간을 삭제하시겠습니까? 관련된 모든 가구와 물건 데이터가 삭제될 수 있습니다.")) {
      deleteMutation.mutate({ spaceId: id });
    }
  };

  return (
    <Layout>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">공간 관리</h1>
          <p className="text-muted-foreground mt-1">집, 사무실, 교실 등 물건을 보관하는 공간을 관리하세요.</p>
        </div>
        <button
          onClick={() => setIsDialogOpen(true)}
          className="shrink-0 flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground font-semibold rounded-xl shadow-md hover:bg-primary/90 hover:shadow-lg hover:-translate-y-0.5 transition-all"
        >
          <Plus className="w-5 h-5" />
          새 공간 추가
        </button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-48 bg-white border rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : spaces.length === 0 ? (
        <EmptyState
          title="등록된 공간이 없습니다"
          description="새로운 공간을 추가하고 평면도에 가구를 배치하여 물건 관리를 시작해보세요."
          action={
            <button
              onClick={() => setIsDialogOpen(true)}
              className="mt-4 flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground font-bold rounded-xl shadow-lg hover:shadow-xl transition-all"
            >
              <Plus className="w-5 h-5" /> 첫 공간 만들기
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {spaces.map((space) => (
            <motion.div
              key={space.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              <Link 
                href={`/spaces/${space.id}/map`}
                className="group block h-full bg-white rounded-2xl p-6 border shadow-sm hover:shadow-xl hover:border-primary transition-all duration-300 relative overflow-hidden"
              >
                <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary to-accent opacity-0 group-hover:opacity-100 transition-opacity" />
                
                <div className="flex justify-between items-start mb-4">
                  <div className="p-3 bg-secondary text-foreground rounded-xl group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                    {getContextIcon(space.context)}
                  </div>
                  <button 
                    onClick={(e) => handleDelete(e, space.id)}
                    className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors z-10"
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <h3 className="text-xl font-bold text-foreground mb-1">{space.name}</h3>
                <p className="text-sm font-medium text-muted-foreground mb-4">
                  {space.context ? SPACE_CONTEXT_LABELS[space.context] || space.context : "기타 공간"}
                </p>
                
                {space.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                    {space.description}
                  </p>
                )}
                
                <div className="flex items-center text-sm font-semibold text-primary mt-auto pt-4 border-t">
                  <Map className="w-4 h-4 mr-2" />
                  평면도 보기 & 가구 관리
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}

      {/* Simple Dialog for Create */}
      {isDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-6 border-b">
              <h2 className="text-2xl font-bold text-foreground">새 공간 추가</h2>
              <p className="text-sm text-muted-foreground mt-1">새로운 관리 영역을 생성합니다.</p>
            </div>
            
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-1.5">공간 이름 *</label>
                <input
                  required
                  type="text"
                  maxLength={60}
                  className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                  placeholder="예: 우리집, 3학년 2반..."
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                />
              </div>
              
              <div>
                <label className="block text-sm font-semibold mb-1.5">공간 유형</label>
                <select
                  className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                  value={formData.context}
                  onChange={(e) => setFormData({...formData, context: e.target.value as any})}
                >
                  <option value="home">집</option>
                  <option value="office">사무실</option>
                  <option value="classroom">교실</option>
                  <option value="other">기타</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold mb-1.5">설명 (선택)</label>
                <textarea
                  className="w-full px-4 py-3 rounded-xl border bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all resize-none"
                  rows={3}
                  placeholder="공간에 대한 간단한 설명..."
                  value={formData.description}
                  onChange={(e) => setFormData({...formData, description: e.target.value})}
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setIsDialogOpen(false)}
                  className="flex-1 px-4 py-3 rounded-xl font-semibold bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="flex-1 px-4 py-3 rounded-xl font-semibold bg-primary text-primary-foreground shadow-lg shadow-primary/20 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-50"
                >
                  {createMutation.isPending ? "생성 중..." : "공간 생성"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Layout>
  );
}
